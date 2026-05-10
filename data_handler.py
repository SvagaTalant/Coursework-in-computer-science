import pandas as pd
import io
import warnings
import re
import difflib

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

COLUMN_KEYWORDS = {
    'date': ['дата', 'date', 'час', 'time', 'транзакція', 'transaction', 'дата операції', 'day', 'термін'],
    'category': ['категорія', 'category', 'опис', 'description', 'тип', 'призначення', 'merchant', 'торговець', 'деталі'],
    'amount': ['сума', 'amount', 'сума операції', 'витрата', 'списання', 'сума в валюті', 'money', 'value', 'total']
}

def _find_column(columns, target_key):
    """Глибокий пошук колонок з підтримкою нечіткого порівняння."""
    keywords = COLUMN_KEYWORDS.get(target_key, [])
    columns_map = {str(col).lower().strip(): col for col in columns}
    
    for clean_col, original_col in columns_map.items():
        for key in keywords:
            if key in clean_col or clean_col in key:
                return original_col
                
    for clean_col, original_col in columns_map.items():
        words = re.findall(r'\w+', clean_col)
        for word in words:
            matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.6)
            if matches:
                return original_col
    return None

def _clean_amount(value):
    """Очищення суми від символів валют та форматування."""
    if pd.isna(value): return 0.0
    s = str(value).replace(',', '.').strip()
    s = re.sub(r'[^\d.-]', '', s)
    try: return float(s)
    except ValueError: return 0.0

def _detect_subscriptions(df_expenses):
    """Виявлення регулярних платежів."""
    subs = []
    if df_expenses.empty: return pd.DataFrame()
    df = df_expenses.copy()
    df['Amount_Int'] = df['Amount_Clean'].astype(int)
    grouped = df.groupby(['Category_Clean', 'Amount_Int'])
    
    for (cat, amt), group in grouped:
        if len(group) >= 2:
            group = group.sort_values('Date_Clean')
            group['Days_Diff'] = group['Date_Clean'].diff().dt.days
            is_monthly = group['Days_Diff'].between(25, 35).any()
            if is_monthly:
                subs.append({'Категорія': cat, 'Сума': abs(amt), 'Періодичність': 'Щомісячна'})
                
    return pd.DataFrame(subs)

def _load_dataframe(file):
    """Інтелектуальне завантаження файлу з пошуком правильного рядка заголовків."""
    filename = file.name.lower()
    
    if filename.endswith(('.xlsx', '.xls')):
        preview = pd.read_excel(file, nrows=15, header=None)
        file.seek(0)
        skip_idx = 0
        for i, row in preview.iterrows():
            row_str = " ".join(str(val).lower() for val in row.values)
            if any(k in row_str for k in COLUMN_KEYWORDS['date']) and any(k in row_str for k in COLUMN_KEYWORDS['amount']):
                skip_idx = i
                break
        return pd.read_excel(file, skiprows=skip_idx)
        
    else:
        #Логіка CSV файлів
        file.seek(0)
        content = file.read().decode('utf-8-sig', errors='replace')
        lines = content.splitlines()
        
        skip_idx = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if any(k in line_lower for k in COLUMN_KEYWORDS['date']) and any(k in line_lower for k in COLUMN_KEYWORDS['amount']):
                skip_idx = i
                break
                
        sep = ';' if ';' in lines[skip_idx] else ','
        
        return pd.read_csv(io.StringIO("\n".join(lines[skip_idx:])), sep=sep, engine='python', on_bad_lines='skip')

def get_enhanced_stats(file):
    """Головна функція аналізу даних."""
    anomaly_multiplier = 1.4
    min_anomaly_amount = 500.0
    extreme_amount = 10000.0

    df = _load_dataframe(file)

    cols = df.columns.tolist()
    c_date = _find_column(cols, 'date')
    c_cat = _find_column(cols, 'category')
    c_amount = _find_column(cols, 'amount')

    if not all([c_date, c_amount]):
        знайдені_колонки = ", ".join([str(c) for c in cols[:5]])
        raise ValueError(f"Не вдалося знайти колонки Дати або Суми. Програма побачила такі заголовки: {знайдені_колонки}...")

    df['Amount_Clean'] = df[c_amount].apply(_clean_amount)
    df['Date_Clean'] = pd.to_datetime(df[c_date], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date_Clean'])
    
    df_expenses = df[df['Amount_Clean'] < 0].copy()
    if df_expenses.empty: df_expenses = df.copy()
    df_expenses['Amount_Clean'] = df_expenses['Amount_Clean'].abs()
    df_expenses['Category_Clean'] = df[c_cat].fillna('Інше').astype(str) if c_cat else 'Інше'

    stats = df_expenses.groupby('Category_Clean')['Amount_Clean'].agg(['sum', 'mean', 'std']).fillna(0)
    
    df_expenses['Limit'] = df_expenses['Category_Clean'].map(stats['mean']) + anomaly_multiplier * df_expenses['Category_Clean'].map(stats['std'])
    anomalies = df_expenses[
        ((df_expenses['Amount_Clean'] > df_expenses['Limit']) & (df_expenses['Amount_Clean'] > min_anomaly_amount)) |
        (df_expenses['Amount_Clean'] > extreme_amount)
    ].copy()

    total_spent = df_expenses['Amount_Clean'].sum()
    days = max((df_expenses['Date_Clean'].max() - df_expenses['Date_Clean'].min()).days, 1)
    
    subscriptions_df = _detect_subscriptions(df_expenses)

    return {
        "cat_stats": stats.reset_index().rename(columns={'Category_Clean': 'Category', 'sum': 'total'}),
        "total_spent": total_spent,
        "forecast": (total_spent / days) * 30,
        "subscriptions": subscriptions_df,
        "anomalies": anomalies[[c_date, 'Category_Clean', 'Amount_Clean']].rename(
            columns={c_date: 'Дата', 'Category_Clean': 'Категорія', 'Amount_Clean': 'Сума'}
        ),
        "raw_data": df_expenses
    }

def export_report_to_excel(data):
    """Експорт у Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        data['cat_stats'].to_excel(writer, sheet_name='Статистика', index=False)
        if not data['subscriptions'].empty:
            data['subscriptions'].to_excel(writer, sheet_name='Підписки', index=False)
        if not data['anomalies'].empty:
            data['anomalies'].to_excel(writer, sheet_name='Аномалії', index=False)
    return output.getvalue()