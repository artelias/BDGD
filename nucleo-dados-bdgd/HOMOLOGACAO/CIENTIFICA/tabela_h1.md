| Métrica | Moderado publicado | DIST / grupos | WAPE | Melhor baseline (WAPE) | IC95% dif. vs baseline (p.p.) | MAE | RMSE | Viés | R² crescimento | Estado h=1 | Piloto granular |
|---|---|---|---|---|---|---|---|---|---|---|---|
| alimentadores / quantidade | random_forest_painel | 90 / 66 | 3,37% | deriva (3,82%) | [-1,48; 0,38] | 10,4 | 28,1 | -1,8% | -0,040 | experimental | — |
| bancos_capacitores / quantidade | hgb_painel | 87 / 64 | 3,98% | persistencia (4,64%) | [-1,68; 0,75] | 16,7 | 37,9 | 0,9% | -0,009 | experimental | — |
| barramentos / quantidade | persistencia | 60 / 38 | 2,60% | crescimento_geometrico (3,16%) | [-2,57; 0,32] | 17,5 | 42,5 | -1,8% | -0,041 | experimental | — |
| chaves / quantidade | ridge_painel | 86 / 62 | 2,93% | persistencia (5,81%) | [-3,38; -2,35] | 1.394 | 4.211 | -2,2% | -0,085 | validado (restrições) | — |
| circuitos_at / quantidade | ridge_painel_ext | 35 / 15 | 4,87% | persistencia (6,16%) | [-3,43; 0,86] | 10,4 | 24,1 | -1,7% | -0,140 | experimental | — |
| conjuntos / quantidade | persistencia | 90 / 66 | 0,72% | deriva (3,69%) | [-4,79; -1,48] | 0,2 | 1,5 | -0,6% | -0,012 | validado (restrições) | — |
| consumidores / quantidade | ridge_painel | 88 / 65 | 2,56% | persistencia (2,98%) | [-0,72; -0,13] | 25.004 | 54.109 | -2,0% | -0,413 | validado (restrições) | — |
| disjuntores / quantidade | ridge_painel | 53 / 29 | 3,52% | deriva (4,41%) | [-3,14; 0,32] | 16,1 | 35,6 | -1,5% | 0,013 | experimental | — |
| geradores / quantidade | deriva | 90 / 66 | 6,63% | crescimento_geometrico (13,50%) | [-9,79; -2,59] | 2.885 | 9.215 | -0,2% | -0,111 | validado (restrições) | — |
| iluminacao / quantidade | persistencia | 90 / 65 | 5,25% | crescimento_geometrico (6,59%) | [-2,10; -0,37] | 12.278 | 45.039 | -3,6% | -0,195 | validado (restrições) | — |
| medidores / quantidade | knn_analogos | 91 / 66 | 1,12% | deriva (1,58%) | [-0,85; -0,15] | 12.883 | 40.113 | -0,3% | -0,052 | validado (restrições) | — |
| postes / quantidade | random_forest_painel | 91 / 66 | 0,56% | deriva (0,62%) | [-0,35; 0,18] | 3.411 | 7.764 | 0,2% | -0,030 | experimental | — |
| ramais / extensao_km | knn_analogos | 91 / 66 | 3,51% | persistencia (4,57%) | [-1,78; -0,19] | 611 | 1.728 | -0,6% | 0,027 | validado (restrições) | — |
| reatores / quantidade | persistencia | 11 / 3 | 3,58% | deriva (7,17%) | [-13,56; 4,35] | 1,0 | 3,0 | 3,6% | -0,219 | experimental | — |
| rede_at / extensao_km | ridge_painel | 49 / 24 | 2,17% | persistencia (2,01%) | [-0,96; 1,28] | 64,9 | 126 | 0,8% | -0,013 | experimental | — |
| rede_bt / extensao_km | ridge_painel | 91 / 66 | 1,09% | persistencia (1,19%) | [-0,37; 0,21] | 209 | 652 | 0,5% | -0,021 | experimental | sem ganho |
| rede_mt / extensao_km | random_forest_painel | 91 / 66 | 0,63% | deriva (0,76%) | [-0,73; 0,31] | 215 | 709 | 0,3% | 0,127 | experimental | rejeitado |
| reguladores / quantidade | ridge_painel | 82 / 58 | 4,27% | deriva (4,81%) | [-1,49; 0,36] | 24,7 | 59,1 | 1,3% | 0,080 | experimental | — |
| religadores / quantidade | knn_analogos | 86 / 61 | 7,47% | deriva (7,41%) | [-1,79; 2,02] | 120 | 300 | -5,6% | -0,298 | experimental | — |
| seccionalizadores / quantidade | persistencia | 28 / 16 | 6,63% | deriva (6,86%) | [-3,03; 3,40] | 64,4 | 137 | 2,0% | -0,044 | experimental | — |
| subestacoes / quantidade | knn_analogos | 65 / 40 | 2,98% | persistencia (3,22%) | [-0,80; 0,39] | 3,6 | 7,5 | 0,3% | -0,024 | experimental | — |
| torres / quantidade | knn_analogos | 50 / 26 | 2,54% | persistencia (2,40%) | [-1,10; 0,71] | 182 | 322 | 0,8% | -0,141 | experimental | — |
| trafo_dist / potencia_kva | ridge_painel | 88 / 65 | 4,00% | deriva (5,97%) | [-4,89; 0,49] | 100.101 | 540.860 | 2,9% | 0,037 | não homologável | validado restrito (kVA experimental) |
| trafo_dist / quantidade | knn_analogos | 88 / 65 | 0,84% | crescimento_geometrico (0,90%) | [-0,51; 0,36] | 553 | 1.345 | -0,4% | 0,051 | experimental | sem ganho |
| trafo_forca / potencia_kva | persistencia | 60 / 37 | 14,94% | deriva (11,92%) | [-3,49; 14,50] | 415.215 | 1.296.878 | 7,6% | -0,016 | não homologável | — |
| trafo_forca / quantidade | ridge_painel | 61 / 38 | 4,17% | persistencia (4,44%) | [-0,61; 0,22] | 6,3 | 14,0 | -2,5% | -0,042 | experimental | — |
| trafo_medida / quantidade | knn_analogos | 75 / 55 | 13,72% | persistencia (15,96%) | [-4,16; -0,97] | 1.101 | 4.863 | -9,5% | -0,018 | experimental | — |
| ucbt (painel Motor V2) / quantidade | ridge_painel (Moderado de consumidores, reexecutado) | — / — | N/D | — | N/D | N/D | N/D | N/D | N/D | — | sem ganho |
