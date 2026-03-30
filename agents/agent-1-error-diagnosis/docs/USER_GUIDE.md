# USER GUIDE -- Agent 1: Huong dan su dung hang ngay

## Khi nao toi nhan duoc thong bao?
Ban se nhan Teams card khi:
  - Job ETL bi loi va agent chua gui card cho loi nay truoc do
  - Cung job bi loi lan moi (sau khi retry that bai)
  - Job TRANSIENT het so lan retry (MAX_REACHED)
  - NiFi processor bao loi tren Bulletin Board

## Doc Teams card nhu the nao?

  [ID] Job ID / Processor ID: so dinh danh de tra cuu trong DB/NiFi
  Nhom loi  : TRANSIENT (tam thoi) / DATA_QUALITY / CONFIGURATION / ...
  Muc do    : CRITICAL(do)/HIGH(cam)/MEDIUM(vang)/LOW(xanh)
  Retry     : Co lan X/Y | TRIGGERED -> agent dang tu xu ly
              Khong       -> can xu ly thu cong
              MAX_REACHED -> het retry, can DE Lead vao cuoc
  LLM Steps : 3 buoc de xuat, doc tu tren xuong

## Cac truong hop can xu ly thu cong

  1. Retry = Khong (DATA_QUALITY, CONFIGURATION, SOURCE_UNAVAILABLE, RESOURCE)
     -> Doc Root Cause va LLM Steps -> Fix nguyen nhan -> chay lai job thu cong

  2. Retry = MAX_REACHED
     -> Lien he DE Lead, cung cap Job ID va Error Detail trong card
     -> DE Lead fix nguyen nhan, reset retry_count trong diagnosis_log:
        UPDATE agent_log.diagnosis_log SET retry_count=0, retry_status=NULL
        WHERE job_id=[ID] AND processed_at >= NOW() - INTERVAL '1 hour';

  3. UNKNOWN (LLM khong phan loai duoc)
     -> Xem Error Detail nguyen ven trong card
     -> Tra cuu trong NiFi bulletin board de co them context
     -> Chuyen cho DE Lead neu khong ro

## Tat retry tam thoi (khi can maintenance)
  # Sua .env:
  RETRY_ENABLED=false
  # Agent se van alert Teams nhung khong trigger NiFi Luong 3

## Tang so lan retry khan cap
  # Khong can restart agent:
  export MAX_RETRIES=5
  # Agent doc gia tri moi o poll cycle tiep theo
