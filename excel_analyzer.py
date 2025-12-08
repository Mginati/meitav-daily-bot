"""
Excel Analyzer
==============
ניתוח דוחות Excel ממיטב
"""

import os
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ExcelAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.sheets = {}
        self._load_file()
    
    def _load_file(self):
        """טעינת הקובץ"""
        try:
            xlsx = pd.ExcelFile(self.file_path)
            for sheet_name in xlsx.sheet_names:
                try:
                    self.sheets[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
                except Exception as e:
                    logger.warning(f"Could not load sheet {sheet_name}: {e}")
            logger.info(f"Loaded {len(self.sheets)} sheets")
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
    
    def analyze(self) -> str:
        """ניתוח מלא של הדוח והחזרת סיכום"""
        report_lines = []
        
        # כותרת
        report_lines.append("╔══════════════════════════════════╗")
        report_lines.append("║  📊 *דוח יומי מיטב*              ║")
        report_lines.append("╚══════════════════════════════════╝\n")
        
        # ריג'קטים בהצטרפות
        rejects = self._analyze_rejects()
        if rejects['count'] > 0:
            report_lines.append(f"🔴 *ריג'קטים בהצטרפות: {rejects['count']}*")
            for reject in rejects['items'][:5]:  # מקסימום 5
                report_lines.append(f"  • {reject['name']} - {reject['reason']}")
            report_lines.append("")
        else:
            report_lines.append("✅ *אין ריג'קטים בהצטרפות*\n")
        
        # ממתינים להפקדה ראשונה
        pending = self._analyze_pending_deposits()
        if pending['count'] > 0:
            report_lines.append(f"⏳ *ממתינים להפקדה ראשונה: {pending['count']}*")
            for item in pending['items'][:5]:
                report_lines.append(f"  • {item['name']} - {item['product']}")
            report_lines.append("")
        
        # צפי ניוד נכנס
        transfers_in = self._analyze_transfers_in()
        if transfers_in['count'] > 0:
            report_lines.append(f"📥 *צפי ניוד נכנס: {transfers_in['count']}*")
            if transfers_in.get('total_amount'):
                report_lines.append(f"  💰 סה\"כ: ₪{transfers_in['total_amount']:,.0f}")
            for item in transfers_in['items'][:3]:
                report_lines.append(f"  • {item['name']}")
            report_lines.append("")
        
        # ניוד יוצא
        transfers_out = self._analyze_transfers_out()
        if transfers_out['count'] > 0:
            report_lines.append(f"📤 *ניוד יוצא: {transfers_out['count']}*")
            for item in transfers_out['items'][:3]:
                report_lines.append(f"  • {item['name']}")
            report_lines.append("")
        
        # הצטרפויות חדשות
        new_joins = self._analyze_new_joins()
        if new_joins['count'] > 0:
            report_lines.append(f"🆕 *הצטרפויות חדשות: {new_joins['count']}*")
            for item in new_joins['items'][:3]:
                report_lines.append(f"  • {item['name']} - {item['product']}")
            report_lines.append("")
        
        # סיכום
        report_lines.append("─────────────────────────────────")
        report_lines.append(f"📅 עודכן: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        return "\n".join(report_lines)
    
    def _analyze_rejects(self) -> Dict[str, Any]:
        """ניתוח ריג'קטים"""
        result = {'count': 0, 'items': []}
        
        # חיפוש גיליון ריג'קטים
        reject_sheets = [
            'ריג\'קטים בהצטרפות',
            'ריגקטים בהצטרפות',
            'rejects'
        ]
        
        df = None
        for sheet_name in self.sheets:
            if any(reject in sheet_name for reject in reject_sheets):
                df = self.sheets[sheet_name]
                break
        
        # גם בודק בגיליון מעקב הצטרפויות
        if df is None or df.empty:
            for sheet_name in self.sheets:
                if 'מעקב הצטרפויות' in sheet_name:
                    temp_df = self.sheets[sheet_name]
                    # מחפש שורות עם סטטוס ריג'קט/דחייה
                    status_cols = [col for col in temp_df.columns if 'סטטוס' in str(col)]
                    for col in status_cols:
                        mask = temp_df[col].astype(str).str.contains('דחי|ריג\'קט|reject', case=False, na=False)
                        if mask.any():
                            df = temp_df[mask]
                            break
        
        if df is not None and not df.empty:
            result['count'] = len(df)
            
            # חיפוש עמודות רלוונטיות
            name_col = self._find_column(df, ['שם', 'עמית', 'name'])
            reason_col = self._find_column(df, ['סיבה', 'תיאור', 'reason', 'ריג\'קט'])
            
            for _, row in df.head(10).iterrows():
                name = str(row[name_col]) if name_col else 'לא ידוע'
                reason = str(row[reason_col]) if reason_col else 'לא צוין'
                
                # קיצור הסיבה
                if len(reason) > 30:
                    reason = reason[:30] + '...'
                
                result['items'].append({
                    'name': name,
                    'reason': reason
                })
        
        return result
    
    def _analyze_pending_deposits(self) -> Dict[str, Any]:
        """ניתוח ממתינים להפקדה ראשונה"""
        result = {'count': 0, 'items': []}
        
        for sheet_name in self.sheets:
            if 'מעקב הצטרפויות' in sheet_name:
                df = self.sheets[sheet_name]
                
                # מחפש שורות עם סטטוס "ממתין להפקדה"
                status_cols = [col for col in df.columns if 'סטטוס' in str(col)]
                for col in status_cols:
                    mask = df[col].astype(str).str.contains('ממתין.*הפקדה|הפקדה ראשונה', case=False, na=False)
                    if mask.any():
                        filtered_df = df[mask]
                        result['count'] += len(filtered_df)
                        
                        name_col = self._find_column(filtered_df, ['שם', 'עמית'])
                        product_col = self._find_column(filtered_df, ['מוצר', 'קופה', 'product'])
                        
                        for _, row in filtered_df.head(10).iterrows():
                            result['items'].append({
                                'name': str(row[name_col]) if name_col else 'לא ידוע',
                                'product': str(row[product_col]) if product_col else ''
                            })
        
        return result
    
    def _analyze_transfers_in(self) -> Dict[str, Any]:
        """ניתוח צפי ניוד נכנס"""
        result = {'count': 0, 'items': [], 'total_amount': 0}
        
        transfer_sheets = ['העברה פנימה', 'ניוד נכנס', 'transfer in']
        
        for sheet_name in self.sheets:
            if any(t in sheet_name.lower() for t in transfer_sheets):
                df = self.sheets[sheet_name]
                if not df.empty:
                    result['count'] = len(df)
                    
                    name_col = self._find_column(df, ['שם', 'עמית'])
                    amount_col = self._find_column(df, ['סכום', 'יתרה', 'amount'])
                    
                    for _, row in df.head(5).iterrows():
                        result['items'].append({
                            'name': str(row[name_col]) if name_col else 'לא ידוע'
                        })
                        
                        if amount_col:
                            try:
                                result['total_amount'] += float(row[amount_col])
                            except:
                                pass
        
        return result
    
    def _analyze_transfers_out(self) -> Dict[str, Any]:
        """ניתוח ניוד יוצא"""
        result = {'count': 0, 'items': []}
        
        transfer_sheets = ['העברה החוצה', 'ניוד יוצא', 'transfer out']
        
        for sheet_name in self.sheets:
            if any(t in sheet_name.lower() for t in transfer_sheets):
                df = self.sheets[sheet_name]
                if not df.empty:
                    result['count'] = len(df)
                    
                    name_col = self._find_column(df, ['שם', 'עמית'])
                    
                    for _, row in df.head(5).iterrows():
                        result['items'].append({
                            'name': str(row[name_col]) if name_col else 'לא ידוע'
                        })
        
        return result
    
    def _analyze_new_joins(self) -> Dict[str, Any]:
        """ניתוח הצטרפויות חדשות"""
        result = {'count': 0, 'items': []}
        
        for sheet_name in self.sheets:
            if 'הצטרפויות' in sheet_name and 'מעקב' not in sheet_name:
                df = self.sheets[sheet_name]
                if not df.empty:
                    result['count'] = len(df)
                    
                    name_col = self._find_column(df, ['שם', 'עמית'])
                    product_col = self._find_column(df, ['מוצר', 'קופה', 'product'])
                    
                    for _, row in df.head(5).iterrows():
                        result['items'].append({
                            'name': str(row[name_col]) if name_col else 'לא ידוע',
                            'product': str(row[product_col]) if product_col else ''
                        })
        
        return result
    
    def _find_column(self, df: pd.DataFrame, keywords: List[str]) -> str:
        """מציאת עמודה לפי מילות מפתח"""
        for col in df.columns:
            col_str = str(col).lower()
            for keyword in keywords:
                if keyword.lower() in col_str:
                    return col
        return None
