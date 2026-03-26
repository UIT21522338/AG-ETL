# Few-shot examples cho LLM

## Example 1 - TRANSIENT
Input:
	job_name: bronze.OM_SalesOrd, layer: bronze, env: DEV
	error_category: TRANSIENT, error: connection timeout to PostgreSQL port=5432

Output:
{
	"root_cause_summary": "Kết nối đến PostgreSQL target bị timeout, có thể do tải DB cao hoặc network tạm thời không ổn định.",
	"suggested_steps": ["Kiểm tra connection pool của PostgreSQL (pg_stat_activity)", "Xem xét tăng timeout trong NiFi DBCPConnectionPool", "Monitor network latency giữa NiFi và DB server"],
	"severity": "MEDIUM",
	"estimated_fix_time": "15-30 phút",
	"escalate_to_de_lead": false
}

## Example 2 - DATA_QUALITY
Input:
	job_name: silver.OM_SalesOrd_Clean, layer: silver, env: DEV
	error_category: DATA_QUALITY, error: null value in column "customer_id" violates not-null constraint

Output:
{
	"root_cause_summary": "Dữ liệu nguồn có giá trị NULL ở cột customer_id, vi phạm ràng buộc NOT NULL của bảng target.",
	"suggested_steps": ["Kiểm tra dữ liệu nguồn: SELECT COUNT(*) FROM source WHERE customer_id IS NULL", "Xem xét thêm bộ lọc NULL trong NiFi flow trước khi insert", "Báo cáo data quality issue lên team nguồn dữ liệu"],
	"severity": "HIGH",
	"estimated_fix_time": "30-60 phút",
	"escalate_to_de_lead": false
}

## Example 3 - UNKNOWN
Input:
	job_name: silver.HR_Payroll, layer: silver, env: DEV
	error_category: UNKNOWN, error: unknown critical error in payroll processor

Output:
{
	"root_cause_summary": "Lỗi không xác định được nguyên nhân tự động. Cần DE Team điều tra log chi tiết.",
	"suggested_steps": ["Xem NiFi processor log chi tiết trong Bulletin Board", "Kiểm tra system log trên NiFi node", "Escalate ngay cho DE Lead để điều tra"],
	"severity": "HIGH",
	"estimated_fix_time": "Cần điều tra",
	"escalate_to_de_lead": true
}
