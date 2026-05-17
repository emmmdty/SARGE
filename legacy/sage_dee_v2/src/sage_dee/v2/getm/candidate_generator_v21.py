from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from re import Pattern
from typing import Any

from sage_dee.v2.contracts.surface import SurfaceCandidate, SurfaceMemory
from sage_dee.v2.csg.surface_memory import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CONTEXT_WINDOW,
    _clean_surface,
    _context,
    _document_text_sources,
    build_surface_memory,
)
from sage_dee.v2.data_interface.dataset_loader import V2DocumentInput


@dataclass(frozen=True)
class V21SurfaceRuleSpec:
    rule_name: str
    target_roles: tuple[str, ...]
    pattern: Pattern[str]
    rationale: str
    risk: str
    group: str | int = 0


V21_SURFACE_RULES: tuple[V21SurfaceRuleSpec, ...] = (
    V21SurfaceRuleSpec(
        rule_name="v21_executive_position",
        target_roles=("高管职位", "变动后职位"),
        pattern=re.compile(r"董事长|总经理|副总经理|董秘|董事会秘书|监事|董事|财务总监|首席财务官|独立董事"),
        rationale=(
            "RC-0 found zero candidate coverage for executive-position roles despite "
            "near-complete content coverage."
        ),
        risk="May surface generic board titles that are not event arguments.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_change_type",
        target_roles=("变动类型", "环节"),
        pattern=re.compile(r"解除质押|被立案|被调查|辞职|离任|聘任|任命|增持|减持|质押|收购|转让"),
        rationale="Strict roles often require short action labels that frozen money/date/company rules do not emit.",
        risk="Action words can describe background context rather than the target event.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_reporting_period",
        target_roles=("财报周期",),
        pattern=re.compile(r"前三季度|一季度|半年度|三季度|年度|上半年|年报|中报|季报"),
        rationale="Financial-report period labels were uncovered in RC-0 while appearing verbatim in content.",
        risk="Period words may refer to disclosure text rather than the extracted event.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_financing_round_stem",
        target_roles=("融资轮次",),
        pattern=re.compile(
            r"(?P<surface>Pre[- ]?[A-Z]|[A-Z][0-9+]?|天使)(?:轮)?",
            re.IGNORECASE,
        ),
        group="surface",
        rationale="Financing-round stem labels can be annotated without the trailing 轮 surface.",
        risk="Single-letter round labels can match non-financing English abbreviations.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_financing_round_phrase",
        target_roles=("融资轮次",),
        pattern=re.compile(r"战略融资|定增|增资"),
        rationale="Financing-round labels are short lexical surfaces outside the frozen rule inventory.",
        risk="增资 and 定增 can appear in non-financing-event contexts.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_pledge_object",
        target_roles=("质押物",),
        pattern=re.compile(r"限售股|流通股|股份|股权|股票|持股"),
        rationale="Pledge-object arguments are usually literal equity-object words, not company or money spans.",
        risk="Generic equity-object words have high document frequency and can inflate candidate lists.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_acquisition_target",
        target_roles=("收购标的",),
        pattern=re.compile(r"[0-9]+(?:\.[0-9]+)?%股权|[0-9]+(?:\.[0-9]+)?%股份|标的公司|标的资产|资产包|项目公司|股权|股份"),
        rationale="Acquisition-target labels frequently use short target nouns missed by frozen rules.",
        risk="股权 and 股份 overlap with pledge and share-count contexts.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_institution_role",
        target_roles=("约谈机构", "监管机构", "裁判机构"),
        pattern=re.compile(r"中国证监会|证监会|深交所|上交所|北交所|交易所|仲裁委|银保监会|法院|约谈机构"),
        rationale="Institution roles need regulator/court/exchange surfaces beyond company-fragment matching.",
        risk="Generic institution mentions may be legal references rather than event participants.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_loss_change",
        target_roles=("亏损变化",),
        pattern=re.compile(r"由盈转亏|盈转亏|同比扩大|同比收窄|亏损扩大|亏损收窄|扭亏|转亏|扩大|收窄|增加|减少"),
        rationale="Loss-change arguments are compact status phrases absent from frozen surface rules.",
        risk="May capture analysis prose rather than the normalized event argument.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_listing_stage",
        target_roles=("环节",),
        pattern=re.compile(r"筹备上市|正式上市|终止上市|暂停上市|上市申请|辅导备案|提交注册|注册生效|上市交易|过会"),
        rationale="Company-listing stages were zero-coverage RC-0 roles with phrase-like surface forms.",
        risk="Stage phrases can appear in procedural descriptions outside the final event.",
    ),
    V21SurfaceRuleSpec(
        rule_name="v21_share_quantity",
        target_roles=("交易股票/股份数量", "持股数量"),
        pattern=re.compile(
            r"(?:不超过|不低于|约)?[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:多)?(?:万|亿)?(?=股|股份|张)"
            r"|[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:万|亿)?\s*(?:股|股份|张)"
            r"|持股数量|交易股票/股份数量"
        ),
        rationale="Share-count roles need explicit quantity spans and schema surface labels.",
        risk="Overlaps frozen share_quantity and can duplicate generic share-count mentions.",
    ),
)


def rule_inventory() -> list[dict[str, Any]]:
    return [
        {
            "rule_name": rule.rule_name,
            "target_roles": list(rule.target_roles),
            "pattern": rule.pattern.pattern,
            "rationale": rule.rationale,
            "risk": rule.risk,
        }
        for rule in V21_SURFACE_RULES
    ]


def build_v21_surface_memory(
    document: V2DocumentInput,
    *,
    enable_v21_rules: bool,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> SurfaceMemory:
    frozen = build_surface_memory(document, context_window=context_window, chunk_size=chunk_size)
    if not enable_v21_rules:
        return frozen

    merged = list(frozen.candidates)
    seen = {_candidate_key(candidate) for candidate in merged}
    for candidate in iter_v21_surface_candidates(
        document,
        context_window=context_window,
        chunk_size=chunk_size,
    ):
        key = _candidate_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
    return SurfaceMemory(doc_id=document.doc_id, candidates=merged, source="document_surface_v21")


def iter_v21_surface_candidates(
    document: V2DocumentInput,
    *,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterable[SurfaceCandidate]:
    merged: OrderedDict[tuple[str, int, int, str], dict[str, object]] = OrderedDict()
    for text_source, text in _document_text_sources(document):
        for rule in V21_SURFACE_RULES:
            for surface, start, end in _rule_matches(rule, text):
                normalized_surface = _clean_surface(surface)
                if not normalized_surface:
                    continue
                key = (text_source, start, end, normalized_surface)
                if key not in merged:
                    merged[key] = {
                        "text_source": text_source,
                        "surface": normalized_surface,
                        "context": _context(text, start, end, context_window),
                        "chunk_id": f"chunk_{start // chunk_size:04d}",
                        "char_start": start,
                        "char_end": end,
                        "rule_names": [],
                    }
                rule_names = merged[key]["rule_names"]
                assert isinstance(rule_names, list)
                if rule.rule_name not in rule_names:
                    rule_names.append(rule.rule_name)

    for row in merged.values():
        rule_names = tuple(str(name) for name in row["rule_names"])
        surface = str(row["surface"])
        text_source = str(row["text_source"])
        char_start = int(row["char_start"])
        char_end = int(row["char_end"])
        yield SurfaceCandidate(
            candidate_id=_candidate_id(document.doc_id, text_source, char_start, char_end, surface, rule_names),
            doc_id=document.doc_id,
            surface=surface,
            context=str(row["context"]),
            chunk_id=str(row["chunk_id"]),
            source="rule",
            char_start=char_start,
            char_end=char_end,
            metadata={
                "rule_names": list(rule_names),
                "text_source": text_source,
                "v21_rule": True,
            },
        )


def _rule_matches(rule: V21SurfaceRuleSpec, text: str) -> Iterable[tuple[str, int, int]]:
    for match in rule.pattern.finditer(text):
        if isinstance(rule.group, str):
            surface = match.group(rule.group)
            start, end = match.span(rule.group)
        else:
            surface = match.group(rule.group)
            start, end = match.span(rule.group)
        yield surface, start, end


def _candidate_key(candidate: SurfaceCandidate) -> tuple[str, int | None, int | None, str]:
    text_source = str(candidate.metadata.get("text_source") or "content")
    return (text_source, candidate.char_start, candidate.char_end, candidate.surface)


def _candidate_id(
    doc_id: str,
    text_source: str,
    char_start: int,
    char_end: int,
    surface: str,
    rule_names: tuple[str, ...],
) -> str:
    raw_key = "\t".join((doc_id, text_source, str(char_start), str(char_end), surface, "|".join(rule_names)))
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:12]
    return f"{doc_id}:csgv21:{digest}"
