import pytest

"""
Contract test stubs for apps/api endpoints (/api/health, /api/search, /api/analyses).
These verify the contract between evaluation/client consumers and the API backend (Engineer 1 / Lead).
Currently skipped until the API service is deployed and accessible in the test environment.
"""

@pytest.mark.skip(reason="API backend implementation is pending (Engineer 1 dependency)")
def test_api_health_contract():
    """التحقق من عقد واجهة فحص الحالة /api/health ومطابقة الحالة 200 والكائنات الأساسية."""
    # Expected contract:
    # GET /api/health -> 200 OK {"status": "ok", "version": "...", "database": "connected"}
    pass

@pytest.mark.skip(reason="API backend implementation is pending (Engineer 1 dependency)")
def test_api_search_contract_and_schema():
    """التحقق من عقد البحث الاسترجاعي /api/search وإرجاع وثائق ومعرفات الأدلة المطلوبة للتقييم."""
    # Expected contract:
    # POST /api/search {"query": "microgravity combustion", "top_k": 5}
    # -> 200 OK {"results": [{"doc_id": "...", "text": "...", "score": 0.95}]}
    pass

@pytest.mark.skip(reason="API backend implementation is pending (Engineer 1 dependency)")
def test_api_search_empty_query_returns_400():
    """التحقق من إرجاع رمز خطأ 400 عند تمرير استعلام فارغ."""
    pass

@pytest.mark.skip(reason="API backend implementation is pending (Engineer 1 dependency)")
def test_api_analyses_contract():
    """التحقق من عقد التحليلات متعددة الوسائط /api/analyses ونماذج النتائج."""
    pass
