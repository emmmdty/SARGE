| Asset | Dataset | Split | Seed | Status | Log | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dueefin_dev_seed17_lrd_invalid_k4_pool | DuEE-Fin | dev | 17 | invalid | - | Invalid for model comparison: postprocess flattened all k=4 candidates (2692 events in, 2444 out), causing FP explosion. |
| dueefin_test_seed17_hf4bin_k1_running | DuEE-Fin | test | 17 | running | logs/sarge_infer_DuEE-Fin-dev500_test_seed17_4bitNF4_k1_20260521T2141Z.log | Running on GPU0 at registry creation; do not enter main table until eval exists. |
| dueefin_test_seed42_hf4bin_k1_running | DuEE-Fin | test | 42 | running | logs/sarge_infer_DuEE-Fin-dev500_test_seed42_4bitNF4_k1_20260521T2221Z.log | Running on GPU0 at registry creation; do not enter main table until eval exists. |
| chfinann_train_seed17_running | ChFinAnn | train | 17 | training | logs/sarge_sft_ChFinAnn-Doc2EDAG_s17_ep2_gpu1_20260521T143813Z.log | Running on GPU1 at registry creation; queue will start seed42 after completion. |
| chfinann_train_seed42_queued | ChFinAnn | train | 42 | training | logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log | Queued behind ChFinAnn seed17 on GPU1 at registry creation. |
