============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Tejas\Desktop\Edme\ims-backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Tejas\Desktop\Edme\ims-backend
plugins: anyio-4.15.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 33 items

tests/test_audit.py::test_tc001_audit_logs_table_schema PASSED           [  3%]
tests/test_audit.py::test_tc002_user_login_success_audit PASSED          [  6%]
tests/test_audit.py::test_tc003_login_failure_user_not_found PASSED      [  9%]
tests/test_audit.py::test_tc004_login_failure_wrong_password PASSED      [ 12%]
tests/test_audit.py::test_tc005_user_logout_audit PASSED                 [ 15%]
tests/test_audit.py::test_tc006_password_changed_audit PASSED            [ 18%]
tests/test_audit.py::test_tc007_claim_submitted_audit PASSED             [ 21%]
tests/test_audit.py::test_tc008_claim_fraud_flagged_audit PASSED         [ 24%]
tests/test_audit.py::test_tc009_claim_status_auto_changed_audit PASSED   [ 27%]
tests/test_audit.py::test_tc010_claim_status_admin_changed_audit PASSED  [ 30%]
tests/test_audit.py::test_tc011_claim_document_uploaded_audit PASSED     [ 33%]
tests/test_audit.py::test_tc012_claim_withdrawn_audit PASSED             [ 36%]
tests/test_audit.py::test_tc013_policy_activated_audit PASSED            [ 39%]
tests/test_audit.py::test_tc014_policy_duplicate_attempt_audit PASSED    [ 42%]
tests/test_audit.py::test_tc015_policy_auto_renew_toggled_audit PASSED   [ 45%]
tests/test_audit.py::test_tc016_user_registered_audit PASSED             [ 48%]
tests/test_audit.py::test_tc017_risk_profile_updated_audit PASSED        [ 51%]
tests/test_audit.py::test_tc018_recommendations_generated_audit PASSED   [ 54%]
tests/test_audit.py::test_tc019_login_failure_no_session PASSED          [ 57%]
tests/test_audit.py::test_tc020_rollback_no_orphan_audit PASSED          [ 60%]
tests/test_audit.py::test_tc021_audit_log_unfiltered_pagination PASSED   [ 63%]
tests/test_audit.py::test_tc022_category_filter PASSED                   [ 66%]
tests/test_audit.py::test_tc023_severity_filter_multi PASSED             [ 69%]
tests/test_audit.py::test_tc024_date_range_filter PASSED                 [ 72%]
tests/test_audit.py::test_tc025_actor_email_partial_match PASSED         [ 75%]
tests/test_audit.py::test_tc026_entity_type_filter PASSED                [ 78%]
tests/test_audit.py::test_tc027_combined_and_filters PASSED              [ 81%]
tests/test_audit.py::test_tc028_empty_result_200 PASSED                  [ 84%]
tests/test_audit.py::test_tc029_export_csv_structure PASSED              [ 87%]
tests/test_audit.py::test_tc030_exported_event_written PASSED            [ 90%]
tests/test_audit.py::test_tc031_non_admin_403 PASSED                     [ 93%]
tests/test_audit.py::test_tc032_no_modification_endpoints PASSED         [ 96%]
tests/test_audit.py::test_tc033_exported_event_before_stream PASSED      [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Tejas\Desktop\Edme\ims-backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

models.py:114
  C:\Users\Tejas\Desktop\Edme\ims-backend\models.py:114: SAWarning: Attribute name 'metadata' should be left reserved for the MetaData instance when using a Declarative class.
    class AuditLog(Base):

schemas.py:48
  C:\Users\Tejas\Desktop\Edme\ims-backend\schemas.py:48: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class ClaimResponse(BaseModel):

schemas.py:63
  C:\Users\Tejas\Desktop\Edme\ims-backend\schemas.py:63: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class UserPolicyResponse(BaseModel):

schemas.py:83
  C:\Users\Tejas\Desktop\Edme\ims-backend\schemas.py:83: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class AdminLogResponse(BaseModel):

schemas.py:108
  C:\Users\Tejas\Desktop\Edme\ims-backend\schemas.py:108: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class AuditLogResponse(BaseModel):

tests/test_audit.py::test_tc017_risk_profile_updated_audit
tests/test_audit.py::test_tc018_recommendations_generated_audit
  C:\Users\Tejas\Desktop\Edme\ims-backend\routers\risk_profile.py:64: PydanticDeprecatedSince211: Accessing the 'model_fields' attribute on the instance is deprecated. Instead, you should access this attribute from the model class. Deprecated in Pydantic V2.11 to be removed in V3.0.
    "changed_fields": list(request.model_fields.keys())

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 33 passed, 8 warnings in 40.33s =======================
