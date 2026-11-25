# Phụ lục: Danh mục kết quả từng ca kiểm thử

Nguồn: `test-results/20261027-final/results.json`, ngày 27/10/2026. Danh mục này chỉ ghi kết quả lần cuối; xem báo cáo 10 để biết lỗi trước sửa và các hạng mục chưa chạy.

[Kế hoạch và đặc tả](09-KE-HOACH-VA-DAC-TA-KIEM-THU.md) · [Báo cáo tổng hợp](10-BAO-CAO-KIEM-THU.md)

## Unit test

| STT | Test ID tự động | Kết quả | Thời gian (giây) |
| ---: | --- | --- | ---: |
| 1 | `test_gemini_grounding.GroundingTests.test_avoid_remains_a_veto_without_enough_sources` | PASS | 0.000000 |
| 2 | `test_gemini_grounding.GroundingTests.test_grounding_request_and_native_evidence` | PASS | 0.016000 |
| 3 | `test_gemini_grounding.GroundingTests.test_model_urls_without_native_citations_do_not_count` | PASS | 0.000000 |
| 4 | `test_gemini_grounding.GroundingTests.test_options_reject_misconfiguration` | PASS | 0.000000 |
| 5 | `test_gemini_grounding.GroundingTests.test_two_subdomains_count_as_one_configured_source` | PASS | 0.000000 |
| 6 | `test_gemini_grounding.GroundingTests.test_untrusted_and_unsafe_urls_are_excluded` | PASS | 0.000000 |
| 7 | `test_research.PolicyTests.test_bad_timezone_and_schedule` | PASS | 0.000000 |
| 8 | `test_research.PolicyTests.test_hourly_timezone_and_net_profit` | PASS | 0.000000 |
| 9 | `test_research.PolicyTests.test_multiple_windows_and_weekdays` | PASS | 0.000000 |
| 10 | `test_research.PolicyTests.test_non_finite_risk_and_invalid_book` | PASS | 0.000000 |
| 11 | `test_research.PolicyTests.test_overnight_uses_start_day` | PASS | 0.015000 |
| 12 | `test_research.PolicyTests.test_risk_budget_position_and_exposure` | PASS | 0.000000 |
| 13 | `test_research.PolicyTests.test_vn_session_boundaries` | PASS | 0.000000 |
| 14 | `test_research.ProviderTests.test_gemini_incomplete_text_is_never_a_vote` | PASS | 0.000000 |
| 15 | `test_research.ProviderTests.test_gemini_request_and_parsing` | PASS | 0.000000 |
| 16 | `test_research.ProviderTests.test_openai_request_and_parsing` | PASS | 0.000000 |
| 17 | `test_research.ProviderTests.test_refusal_and_truncation` | PASS | 0.000000 |
| 18 | `test_research.ProviderTests.test_reject_hallucinated_duplicate_and_invalid_confidence` | PASS | 0.000000 |
| 19 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_dynamic_stake_size_risk_limits` | PASS | 0.000000 |
| 20 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_gemini_interactions_and_legacy_parser` | PASS | 0.000000 |
| 21 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_golden_trading_session_03_to_04_vn` | PASS | 0.000000 |
| 22 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_overnight_trading_session` | PASS | 0.000000 |

## Integration test

| STT | Test ID tự động | Kết quả | Thời gian (giây) |
| ---: | --- | --- | ---: |
| 1 | `test_gemini_grounding.GroundingTests.test_gemini_only_overlay_and_worker` | PASS | 0.000000 |
| 2 | `test_integration.PipelineIntegrationTests.test_grounded_provider_to_snapshot_to_entry_policy` | PASS | 0.047000 |
| 3 | `test_integration.PipelineIntegrationTests.test_worker_cli_invalid_loop_exits_before_importing_ccxt` | PASS | 0.313000 |
| 4 | `test_integration.PipelineIntegrationTests.test_worker_cli_merges_overlay_and_writes_history` | PASS | 0.297000 |
| 5 | `test_integration.TransportIntegrationTests.test_provider_transport_serializes_json_and_rejects_oversized_reply` | PASS | 0.578000 |
| 6 | `test_mock_api.MockApiTests.test_dashboard_is_served` | PASS | 0.000000 |
| 7 | `test_mock_api.MockApiTests.test_forged_bearer_rejected` | PASS | 0.000000 |
| 8 | `test_mock_api.MockApiTests.test_login_read_and_stopbuy_over_http` | PASS | 0.016000 |
| 9 | `test_mock_api.MockApiTests.test_malformed_forceexit_does_not_close_positions` | PASS | 0.016000 |
| 10 | `test_research.ResearchTests.test_advisory_failure_does_not_veto_technical` | PASS | 0.000000 |
| 11 | `test_research.ResearchTests.test_ai_cannot_override_market_veto` | PASS | 0.000000 |
| 12 | `test_research.ResearchTests.test_invalid_quorum_and_threshold` | PASS | 0.016000 |
| 13 | `test_research.ResearchTests.test_missing_stale_or_bad_candles_fail` | PASS | 0.000000 |
| 14 | `test_research.ResearchTests.test_provider_failure_missing_vote_low_confidence_or_veto` | PASS | 0.000000 |
| 15 | `test_research.ResearchTests.test_report_roundtrip_and_expiry` | PASS | 0.000000 |
| 16 | `test_research.ResearchTests.test_required_consensus` | PASS | 0.000000 |
| 17 | `test_research.ResearchTests.test_rsi_and_overlay_merge` | PASS | 0.000000 |
| 18 | `test_research.ResearchTests.test_unavailable_market_and_blacklist` | PASS | 0.000000 |
| 19 | `test_research.ResearchTests.test_unfinished_candle_not_used` | PASS | 0.000000 |
| 20 | `test_research.ResearchTests.test_wrong_exchange_policy_and_pair` | PASS | 0.000000 |
| 21 | `test_strategy.StrategyHookTests.test_entry_accepts_fresh_report_in_session` | PASS | 0.015000 |
| 22 | `test_strategy.StrategyHookTests.test_entry_vetoes_outside_session_and_oversize` | PASS | 0.016000 |
| 23 | `test_strategy.StrategyHookTests.test_entry_vetoes_stale_report_or_missing_file` | PASS | 0.000000 |
| 24 | `test_strategy.StrategyHookTests.test_entry_vetoes_wide_spread_deviation_and_stale_candle` | PASS | 0.000000 |
| 25 | `test_strategy.StrategyHookTests.test_exits_not_blocked_by_schedule_or_broken_report` | PASS | 0.015000 |
| 26 | `test_strategy.StrategyHookTests.test_historical_does_not_read_research_or_orderbook` | PASS | 0.000000 |
| 27 | `test_strategy.StrategyHookTests.test_notification_failure_does_not_block_stoploss` | PASS | 0.016000 |
| 28 | `test_strategy.StrategyHookTests.test_schedule_filters_candle_close_not_open_time` | PASS | 0.016000 |
| 29 | `test_strategy.StrategyHookTests.test_sizing_hook_rejects_exchange_minimum_and_api_failure` | PASS | 0.015000 |
| 30 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_mock_server_research_report` | PASS | 0.000000 |
| 31 | `test_vn_policy.TestVnPolicyAndAiAdvisor.test_multi_ai_consensus_and_veto` | PASS | 0.000000 |

## System test: browser và mock HTTP

| Test ID | Kết quả | Thời gian (ms) |
| --- | --- | ---: |
| `SYS-01-login-dashboard` | PASS | 1093 |
| `SYS-02-invalid-login` | PASS | 754 |
| `SYS-03-stop-and-resume` | PASS | 736 |
| `SYS-04-panic-confirmation` | PASS | 506 |
| `SYS-05-close-single-trade` | PASS | 500 |
| `SYS-06-risk-lock` | PASS | 480 |
| `SYS-07-research-grounding-mobile` | PASS | 570 |
| `SYS-08-file-stale-xss-and-invalid-json` | PASS | 380 |

Một method có nhiều assert/subcase vẫn tính một ca. Bộ Python có 53 ID duy nhất; browser có 8 ca. Không có SKIP/FAIL/ERROR trong lần cuối. Test doubles và giới hạn môi trường được mô tả trong tài liệu 09/10.
