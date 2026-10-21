# Final release evidence index

Deployed/tested application: `ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec`. Restricted source lookup only; generation disabled.

| Evidence | Path | SHA256 |
|---|---|---|
| Code/CI | [ci-final-release.json](ci-final-release.json) | `0f60dbd06c0bad643e4f7d652e56ebfc4c812cb2cb07d3e5a5cc62f473a72982` |
| Frozen candidate | [candidate-final-freeze.json](candidate-final-freeze.json) | `b60b3baa4a973db61a6be944407dd4e1004cadb6c4e23a0683b36d7a72cce4c6` |
| Final image | [image-probe-final.json](image-probe-final.json) | `c9abcb15afed4c51bf4774149f9700ab592b509c72d1b0395df86ebaf4bdcc19` |
| Memory | [docker-memory-ui-guard.log](docker-memory-ui-guard.log) | `1e30265790f277bfce11562f9c95f1cb69c7fa326763ddcf5da7148ee4df3806` |
| Cloud deployment | [render-deploy-final.jsonl](render-deploy-final.jsonl) | `17a19978fc3966ee479f7a5e504adc3cb8ad08477e4e2fb0cb9b327d2d94e73b` |
| Frontend identity | [cloudflare-deployment-final.json](cloudflare-deployment-final.json) | `9e649595713d1cb1db91eeff6a2811902252fdd0f4551bc0b3943808f7aad564` |
| Public JS/CSS | [public-frontend-integrity-final.json](public-frontend-integrity-final.json) | `5c91afa968aaa1d747617f7beffc050aec8aaf9ddc5d049a19bf5f77bb315ef8` |
| Public source/date rejection | [public-source-rejections.json](public-source-rejections.json) | `1002abbfa4640a484e18da4a4775a708bc8f6357719032e8ce91ff89c5e5c9fa` |
| Corpus activation | [corpus-publication.json](corpus-publication.json) | `8661109928eb35c4560012f9e502dcab2270848a7f777e1e5ab1d7d2853cfde5` |
| Cloud PG role/metadata | [post-publication-database.json](post-publication-database.json) | `fd6daf1b4dc1290ac1d6ba8ad692b3e108637f792ce13020243ab401f5d07447` |
| Backup restore | [rollback-restore.json](rollback-restore.json) | `ddc5f24b9c0a487398b5225ce7749aed01e297b36321fb5059a2d5e7a6db05cc` |
| Ingress rejection | [ingress-final-deploy.json](ingress-final-deploy.json) | `64885c321ad754a28b4d0baa4b9bc88206351e7180eaf42d8da20a86353f7d39` |
| Local source API PG | [qa/source-lookup-pg-acceptance.json](qa/source-lookup-pg-acceptance.json) | `bf82e01e083c24a10a91925dc65d690a93c633a36cc52b0fc1c8314203c988a5` |
| Final committed source/gold preservation | [qa/final-code-committed-verification.json](qa/final-code-committed-verification.json) | `7bc90c5f4ff40a1fc1d4791c1f0a3c608481fcee0af0b0b0e94765c4a5b624f5` |
| Latest public browser | [qa/public-source-2026-10-21T11-02-32-079Z/report.json](qa/public-source-2026-10-21T11-02-32-079Z/report.json) | `c4e8c0b56094e1b22710730f8fbb28311a5395d026ff17e2aaaaf9d2eaa43df4` |
| First harness failure | [qa/public-source-2026-10-21T10-26-18-876Z/report.json](qa/public-source-2026-10-21T10-26-18-876Z/report.json) | `71b2b811967afe3759e7ef3bd32248ad9cfea54154f56343023e58a7952af9ea` |
| Harness failure explanation | [qa/public-source-run-01-harness-review.json](qa/public-source-run-01-harness-review.json) | `13b3148ce7b7db0afee0c018d87d27c1f0b74b237ce729e1097259124622524d` |
| Independent C02 failure | [pilot-C02/attempt.json](pilot-C02/attempt.json) | `e1bd4dfd8666504d5e6b859233f834c91de21897a54cf95973f55b282c27ce64` |
| C02 review | [qa/c02-pilot-review.md](qa/c02-pilot-review.md) | `1efcdc5459d470995059ed26f986e22209ce82a4c364d8b075e6300e0bca9717` |
| Reload race and regression | [qa/UI_UNKNOWN_RUNTIME_FIX.md](qa/UI_UNKNOWN_RUNTIME_FIX.md) | `f46fcc79e99d76158b26acb674f914a4184bc04b4273815148962ad801191da4` |
| Public race diagnostic | [qa/history-race-2026-10-21T10-37-55-451Z/report.json](qa/history-race-2026-10-21T10-37-55-451Z/report.json) | `7747dfdf98fac4f5beb9d0fb5e8685420d68d63c338ab54ba126b6faeae34471` |
| Superseded CI failure | [ci-ui-guard-superseded.json](ci-ui-guard-superseded.json) | `2e89906d66e857e862b89e5cd2035ffd72a1ca7f4bd581321a1e509e404b1bb7` |
| Rollback procedure | [ROLLBACK_FINAL.md](ROLLBACK_FINAL.md) | `de55b44df0ed31c708a047e19d2e45d10a831a82ae9dd5188683daa0b2a3ed31` |

Historical evidence and locked suites are preserved; see [Phase 4 index](../final-submission/2026-10-21/EVIDENCE_INDEX.md) and [academic evaluation](../submission-20261021/EVALUATION.md).

The release manifest pins current serving identity. Retrieval metrics and failed model pilots retain their original runtime fingerprints. Local fixture tests do not stand in for public or model acceptance.
