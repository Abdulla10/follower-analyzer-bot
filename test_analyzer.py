"""
اختبار وحدة التحليل
"""
import sys
sys.path.insert(0, '/home/ubuntu/follower_analyzer_bot')

from analyzer import analyze_account, format_number, _analyze_followers, _calculate_rating, _analyze_growth

def test_format_number():
    assert format_number(500) == "500"
    assert format_number(1500) == "1.5K"
    assert format_number(1_500_000) == "1.5M"
    print("✅ test_format_number passed")

def test_analyze_followers():
    result = _analyze_followers(100000, 500, 5.0, False)
    assert "real_percentage" in result
    assert "inactive_percentage" in result
    assert "fake_percentage" in result
    total = result["real_percentage"] + result["inactive_percentage"] + result["fake_percentage"]
    assert 95 <= total <= 105, f"Total percentages should be ~100, got {total}"
    print(f"✅ test_analyze_followers passed — real: {result['real_percentage']}%, inactive: {result['inactive_percentage']}%, fake: {result['fake_percentage']}%")

def test_calculate_rating():
    fa = {"real_percentage": 80}
    ga = {"growth_type": "natural"}
    rating = _calculate_rating(5.0, fa, ga)
    assert "score" in rating
    assert "label" in rating
    assert rating["score"] > 0
    print(f"✅ test_calculate_rating passed — score: {rating['score']}, label: {rating['label']}")

def test_analyze_growth():
    result = _analyze_growth(100000, 200, 3.0)
    assert "growth_type" in result
    assert "growth_label" in result
    print(f"✅ test_analyze_growth passed — type: {result['growth_type']}, label: {result['growth_label']}")

def test_instagram_analysis():
    print("\n🔍 اختبار تحليل Instagram...")
    result = analyze_account("testuser123", "instagram")
    assert result["platform"] == "Instagram"
    assert result["username"] == "testuser123"
    assert "followers" in result
    assert "engagement_rate" in result
    assert "follower_analysis" in result
    assert "growth_analysis" in result
    assert "rating" in result
    print(f"✅ Instagram analysis passed")
    print(f"   المتابعون: {format_number(result['followers'])}")
    print(f"   معدل التفاعل: {result['engagement_rate']}%")
    print(f"   التقييم: {result['rating']['label']} ({result['rating']['score']}/100)")

def test_tiktok_analysis():
    print("\n🔍 اختبار تحليل TikTok...")
    result = analyze_account("testuser456", "tiktok")
    assert result["platform"] == "TikTok"
    assert result["username"] == "testuser456"
    assert "followers" in result
    assert "engagement_rate" in result
    print(f"✅ TikTok analysis passed")
    print(f"   المتابعون: {format_number(result['followers'])}")
    print(f"   معدل التفاعل: {result['engagement_rate']}%")
    print(f"   التقييم: {result['rating']['label']} ({result['rating']['score']}/100)")

def test_report_building():
    from bot import build_report, build_comparison_report
    print("\n📝 اختبار بناء التقارير...")
    
    result = analyze_account("sampleuser", "instagram")
    report = build_report(result)
    assert "@sampleuser" in report
    assert "معدل التفاعل" in report
    assert "تحليل المتابعين" in report
    assert "التقييم النهائي" in report
    print("✅ build_report passed")
    
    result2 = analyze_account("anotheruser", "tiktok")
    comparison = build_comparison_report(result, result2)
    assert "VS" in comparison
    assert "@sampleuser" in comparison
    assert "@anotheruser" in comparison
    print("✅ build_comparison_report passed")

def run_all_tests():
    print("=" * 50)
    print("🧪 بدء اختبارات Follower Analyzer Bot")
    print("=" * 50)
    
    test_format_number()
    test_analyze_followers()
    test_calculate_rating()
    test_analyze_growth()
    test_instagram_analysis()
    test_tiktok_analysis()
    test_report_building()
    
    print("\n" + "=" * 50)
    print("✅ جميع الاختبارات نجحت!")
    print("=" * 50)

if __name__ == "__main__":
    run_all_tests()
