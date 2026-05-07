import streamlit as st
import pandas as pd
import io

# 웹 페이지 기본 설정
st.set_page_config(page_title="광고주 정보 검증 대시보드", layout="wide", page_icon="📊")

# 사내 인트라넷 스타일의 CSS 적용
st.markdown("""
<style>
    /* 전체 배경색 및 폰트 설정 */
    .stApp {
        background-color: #F4F7F6;
        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    }
    
    /* 상단 헤더 숨기기 */
    header {visibility: hidden;}
    
    /* 제목 스타일링 */
    h1 {
        color: #1E3A8A;
        font-weight: 700;
        border-bottom: 2px solid #D1D5DB;
        padding-bottom: 10px;
        margin-bottom: 30px;
    }
    
    h2 {
        color: #374151;
        font-weight: 600;
        margin-top: 30px;
    }

    /* 컨테이너 및 위젯 스타일링 */
    .stFileUploader > div > div {
        background-color: #FFFFFF;
        border: 2px dashed #9CA3AF;
        border-radius: 8px;
        padding: 20px;
    }

    /* 데이터프레임 래퍼 배경 처리 */
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        padding: 10px;
    }
    
    /* 구분선 스타일 */
    hr {
        border-top: 1px solid #E5E7EB;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    /* 알림창 스타일 변경 */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 팀별 광고주 데이터 검증 대시보드 (V3)")

# 엑셀 파일 업로드 UI
st.markdown("#### 📂 파일 업로드")
uploaded_file = st.file_uploader("인트라넷에서 다운로드 받은 엑셀 파일을 여기에 드래그 앤 드롭 하세요.", type=['xlsx'])

if uploaded_file:
    # 데이터 불러오기
    df = pd.read_excel(uploaded_file)
    
    # 1. 완료/미완료 판별 로직 함수 (업데이트 됨)
    def check_status(row):
        # [조건 1] 필수값 공란 또는 'X' 체크
        req_cols = ['광고주명', '업체담당자', '이메일', '사업자번호']
        for col in req_cols:
            val = str(row.get(col, '')).strip()
            if pd.isna(row.get(col)) or val == '' or val.upper() == 'X' or val == 'nan':
                return "미완료"
        
        # [조건 2] 연락처 체크 (휴대전화 기준, '없음'이나 'X' 확인)
        phone = str(row.get('휴대전화', '')).strip()
        if '없음' in phone or 'X' in phone.upper() or phone == '' or phone == 'nan':
            return "미완료"
            
        # [조건 3] 이메일 형식 체크 (@ 포함 여부)
        email = str(row.get('이메일', '')).strip()
        if '@' not in email:
            return "미완료"
            
        # [조건 4 - V3 NEW] 홈페이지 키워드 예외 처리 로직 (11st, coupang, minishop 추가)
        homepage = str(row.get('홈페이지', '')).strip().lower()
        
        # 정상으로 인정해 줄 예외 키워드 목록
        valid_hp_keywords = [
            'pf.kakao', 'smartstore', 'openmarket', 
            '11st', 'coupang', 'minishop'
        ]
        
        # 홈페이지 문자열 안에 위 키워드 중 하나라도 들어있으면 True
        is_valid_hp = any(kw in homepage for kw in valid_hp_keywords)
        
        # 만약 예외 키워드가 포함되지 않았다면, 빈칸/X/없음 인지 추가 확인
        if not is_valid_hp:
            if homepage == '' or homepage == 'nan' or homepage == 'x' or '없음' in homepage:
                return "미완료"
                
        # 모든 관문을 무사히 통과하면 완료!
        return "완료"

    # '검증상태' 열 추가
    df['검증상태'] = df.apply(check_status, axis=1)

    st.markdown("---")

    # 2. 팀별 통계 요약표
    st.header("📈 팀별 데이터 입력 완료율 현황")
    
    # 팀명 기준으로 통계 계산
    stats = df.groupby('팀명')['검증상태'].value_counts().unstack().fillna(0)
    if '완료' not in stats.columns: stats['완료'] = 0
    if '미완료' not in stats.columns: stats['미완료'] = 0
    
    stats['전체 할당건수'] = stats['완료'] + stats['미완료']
    stats['완료율(%)'] = (stats['완료'] / stats['전체 할당건수'] * 100).round(1)
    
    # 보기 좋게 컬럼 순서 정렬
    stats = stats[['전체 할당건수', '완료', '미완료', '완료율(%)']].astype({'전체 할당건수': int, '완료': int, '미완료': int})
    st.dataframe(stats, use_container_width=True)

    st.markdown("---")

    # 3. 미완료 리스트 필터링 조회
    st.header("🚨 미완료 광고주 상세 리스트 (수정 필요)")
    
    # 필터 UI를 두 개의 열로 나누어 배치
    col1, col2 = st.columns([1, 3])
    
    with col1:
        team_list = ['전체 보기'] + list(df['팀명'].dropna().unique())
        selected_team = st.selectbox("조회할 팀을 선택하세요", team_list)
    
    # 필터링 로직
    if selected_team == '전체 보기':
        filtered_df = df[df['검증상태'] == '미완료']
    else:
        filtered_df = df[(df['검증상태'] == '미완료') & (df['팀명'] == selected_team)]
        
    with col2:
        # st.selectbox 와 높이를 맞추기 위해 빈 공간을 약간 추가
        st.write("")
        st.info(f"선택된 팀: **{selected_team}** | 총 **{len(filtered_df)}건**의 누락/오류 데이터가 발견되었습니다.")
    
    # 결과 출력
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")
    st.header("📥 미완료 데이터 다운로드")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.markdown("**현재 조회 중인 데이터 다운로드**")
        st.caption(f"선택하신 '{selected_team}'의 데이터를 엑셀로 다운로드합니다.")
        
        output_current = io.BytesIO()
        with pd.ExcelWriter(output_current, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='미완료_데이터')
            
        st.download_button(
            label=f"⬇️ '{selected_team}' 데이터 다운로드",
            data=output_current.getvalue(),
            file_name=f"미완료리스트_{selected_team}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_dl2:
        st.markdown("**모든 팀 한 번에 다운로드 (시트 분리)**")
        st.caption("각 팀별로 엑셀 하단 시트(Sheet)가 분리된 하나의 파일을 다운로드합니다.")
        
        output_all = io.BytesIO()
        incomplete_all = df[df['검증상태'] == '미완료']
        
        with pd.ExcelWriter(output_all, engine='openpyxl') as writer:
            teams = incomplete_all['팀명'].dropna().unique()
            for team in teams:
                # 엑셀 시트명은 최대 31자까지 가능하며 특수문자 일부 제한됨
                safe_team_name = str(team).replace('/', '_').replace('\\', '_')[:31]
                team_df = incomplete_all[incomplete_all['팀명'] == team]
                team_df.to_excel(writer, index=False, sheet_name=safe_team_name)
                
            if len(teams) == 0:
                pd.DataFrame({"메시지": ["모든 데이터가 완료되었습니다."]}).to_excel(writer, index=False, sheet_name='완료')
                
        st.download_button(
            label="⬇️ 전체 팀 시트별 다운로드",
            data=output_all.getvalue(),
            file_name="미완료리스트_전체팀_시트별.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )