"""
Parser avanzato per bollette energetiche italiane
Supporta multipli fornitori con pattern specifici
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json

@dataclass
class BillData:
    """Struttura dati bolletta"""
    # Identificazione
    fornitore: Optional[str] = None
    numero_cliente: Optional[str] = None
    periodo_fatturazione: Optional[str] = None
    data_emissione: Optional[str] = None
    
    # Consumi
    consumo_mensile_kwh: Optional[float] = None
    consumo_annuo_kwh: Optional[float] = None
    consumo_f1: Optional[float] = None  # Fascia 1 (picco)
    consumo_f2: Optional[float] = None  # Fascia 2
    consumo_f3: Optional[float] = None  # Fascia 3
    consumo_totale_periodo: Optional[float] = None
    
    # Potenza
    potenza_impegnata_kw: Optional[float] = None
    potenza_disponibile_kw: Optional[float] = None
    potenza_max_prelevata_kw: Optional[float] = None
    
    # Costi dettagliati
    spesa_energia: Optional[float] = None
    spesa_materia_energia: Optional[float] = None  # Componente energia pura
    spesa_trasporto_gestione: Optional[float] = None
    spesa_oneri_sistema: Optional[float] = None
    canone_rai: Optional[float] = None
    
    # Imposte
    accise: Optional[float] = None
    iva: Optional[float] = None
    addizionali_locali: Optional[float] = None
    
    # Totali
    subtotale: Optional[float] = None
    totale_bolletta: Optional[float] = None
    totale_da_pagare: Optional[float] = None
    
    # Prezzi unitari
    prezzo_energia_kwh: Optional[float] = None
    prezzo_medio_kwh: Optional[float] = None
    
    # Caratteristiche contratto
    tipo_mercato: Optional[str] = None  # "libero" o "tutelato"
    tipo_prezzo: Optional[str] = None  # "fisso" o "variabile"
    tipo_tariffa: Optional[str] = None  # "monoraria", "bioraria", "trioraria"
    nome_offerta: Optional[str] = None
    
    # Metadata
    confidence_score: float = 0.0
    campi_estratti: int = 0
    campi_totali: int = 30

class EnhancedBillParser:
    """Parser intelligente multi-provider per bollette italiane"""
    
    # Fornitori principali con varianti nome
    PROVIDERS = {
        'enel': ['enel', 'enel energia', 'enel servizio elettrico'],
        'eni': ['eni', 'eni plenitude', 'eni gas e luce'],
        'a2a': ['a2a', 'a2a energia'],
        'edison': ['edison', 'edison energia'],
        'sorgenia': ['sorgenia'],
        'acea': ['acea', 'acea energia'],
        'hera': ['hera', 'hera comm'],
        'iren': ['iren', 'iren mercato'],
        'e.on': ['e.on', 'eon'],
    }
    
    # Pattern regex avanzati per estrazione
    PATTERNS = {
        # CONSUMI - pattern multipli per robustezza
        'consumo_kwh': [
            r'consumo\s+(?:totale|periodo|effettivo)?[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'energia\s+(?:attiva\s+)?consumata[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'totale\s+consumo[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'(\d+(?:[.,]\d+)?)\s*kwh\s+consumat[io]',
            r'kWh\s+(?:consumati|utilizzati)[:\s]+(\d+(?:[.,]\d+)?)',
        ],
        
        # FASCE ORARIE
        'fascia_f1': [
            r'f1[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'fascia\s+f?1[:\s]+(\d+(?:[.,]\d+)?)',
            r'picco[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
        ],
        'fascia_f2': [
            r'f2[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'fascia\s+f?2[:\s]+(\d+(?:[.,]\d+)?)',
        ],
        'fascia_f3': [
            r'f3[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
            r'fascia\s+f?3[:\s]+(\d+(?:[.,]\d+)?)',
            r'fuori\s+picco[:\s]+(\d+(?:[.,]\d+)?)\s*kwh',
        ],
        
        # POTENZA
        'potenza': [
            r'potenza\s+(?:contrattualmente\s+)?impegnata[:\s]+(\d+(?:[.,]\d+)?)\s*kw',
            r'potenza\s+disponibile[:\s]+(\d+(?:[.,]\d+)?)\s*kw',
            r'potenza[:\s]+(\d+(?:[.,]\d+)?)\s*kw',
            r'(\d+(?:[.,]\d+)?)\s*kw\s+impegnat[ao]',
        ],
        'potenza_max': [
            r'potenza\s+massima\s+(?:prelevata|rilevata)[:\s]+(\d+(?:[.,]\d+)?)',
            r'potenza\s+max[:\s]+(\d+(?:[.,]\d+)?)',
        ],
        
        # COSTI ENERGIA
        'spesa_energia': [
            r'spesa\s+per\s+(?:la\s+)?energia[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'energia\s+elettrica[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'materia\s+energia[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'componente\s+energia[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
        ],
        
        # TRASPORTO E GESTIONE
        'spesa_trasporto': [
            r'spesa\s+per\s+(?:il\s+)?trasporto[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'trasporto\s+e\s+gestione[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'distribuzione[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
        ],
        
        # ONERI DI SISTEMA
        'oneri_sistema': [
            r'oneri\s+(?:di\s+)?sistema[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'oneri\s+generali[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
        ],
        
        # IMPOSTE
        'accise': [
            r'accis[ei][:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'imposte\s+erariali[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
        ],
        'iva': [
            r'iva\s+(?:\d+%)?[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'imposta\s+sul\s+valore\s+aggiunto[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
        ],
        
        # TOTALI
        'totale': [
            r'totale\s+(?:da\s+pagare|bolletta|fattura)[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'importo\s+totale[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'da\s+pagare[:\s]+€?\s*(\d+(?:[.,]\d+)?)',
            r'€\s*(\d+(?:[.,]\d+)?)\s+da\s+pagare',
        ],
        
        # TIPO CONTRATTO
        'prezzo_fisso': r'prezzo\s+(?:bloccato|fisso)|tariffa\s+fissa|monorario',
        'prezzo_variabile': r'prezzo\s+(?:variabile|indicizzato)|tariffa\s+variabile',
        
        # PERIODO
        'periodo': [
            r'periodo[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\s*[-–]\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'dal\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\s+al\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        ],
        
        # NUMERO CLIENTE
        'numero_cliente': [
            r'n[°.]?\s*cliente[:\s]+(\w+)',
            r'codice\s+cliente[:\s]+(\w+)',
            r'cliente[:\s]+(\d+)',
        ],
    }
    
    def __init__(self):
        self.bill = BillData()
    
    def parse(self, text: str) -> Dict:
        """
        Parse completo della bolletta
        
        Args:
            text: Testo estratto dalla bolletta (da PDF o OCR)
        
        Returns:
            Dict con tutti i campi estratti
        """
        if not text or len(text.strip()) < 50:
            return self._default_profile()
        
        # Normalizza testo
        text_clean = self._normalize_text(text)
        text_lower = text_clean.lower()
        
        # 1. Identifica fornitore
        self.bill.fornitore = self._extract_provider(text_lower)
        
        # 2. Estrai numero cliente
        self.bill.numero_cliente = self._extract_field(text_lower, self.PATTERNS['numero_cliente'])
        
        # 3. Estrai periodo fatturazione
        self.bill.periodo_fatturazione = self._extract_period(text_lower)
        
        # 4. Estrai consumi
        self._extract_consumption(text_lower)
        
        # 5. Estrai potenza
        self._extract_power(text_lower)
        
        # 6. Estrai costi
        self._extract_costs(text_lower)
        
        # 7. Estrai imposte
        self._extract_taxes(text_lower)
        
        # 8. Estrai totale
        self._extract_totals(text_lower)
        
        # 9. Determina tipo contratto
        self._extract_contract_type(text_lower)
        
        # 10. Calcola campi derivati
        self._calculate_derived_fields()
        
        # 11. Calcola confidence score
        self._calculate_confidence()
        
        return asdict(self.bill)
    
    def _normalize_text(self, text: str) -> str:
        """Normalizza il testo per parsing migliore"""
        # Rimuovi multipli spazi
        text = re.sub(r'\s+', ' ', text)
        # Normalizza separatori decimali
        text = text.replace(',', '.')
        return text.strip()
    
    def _extract_provider(self, text: str) -> Optional[str]:
        """Identifica il fornitore della bolletta"""
        for provider, variants in self.PROVIDERS.items():
            for variant in variants:
                if variant in text:
                    # Capitalizza correttamente
                    return self._format_provider_name(provider)
        return None
    
    def _format_provider_name(self, provider: str) -> str:
        """Formatta nome fornitore"""
        mapping = {
            'enel': 'Enel Energia',
            'eni': 'Eni Plenitude',
            'a2a': 'A2A Energia',
            'edison': 'Edison Energia',
            'sorgenia': 'Sorgenia',
            'acea': 'Acea Energia',
            'hera': 'Hera Comm',
            'iren': 'Iren Mercato',
            'e.on': 'E.ON Energia'
        }
        return mapping.get(provider, provider.upper())
    
    def _extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        """Estrae campo generico con pattern multipli"""
        if isinstance(patterns, str):
            patterns = [patterns]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_float(self, text: str, patterns: List[str]) -> Optional[float]:
        """Estrae valore numerico float"""
        value_str = self._extract_field(text, patterns)
        if value_str:
            try:
                # Rimuovi caratteri non numerici tranne punto
                cleaned = re.sub(r'[^\d.]', '', value_str)
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def _extract_period(self, text: str) -> Optional[str]:
        """Estrae periodo di fatturazione"""
        for pattern in self.PATTERNS['periodo']:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) >= 2:
                    return f"{match.group(1)} - {match.group(2)}"
        return None
    
    def _extract_consumption(self, text: str):
        """Estrae tutti i dati sui consumi"""
        # Consumo totale
        consumo = self._extract_float(text, self.PATTERNS['consumo_kwh'])
        
        if consumo:
            # Determina se mensile o annuo (euristica)
            if consumo < 1000:  # Probabilmente mensile
                self.bill.consumo_mensile_kwh = consumo
                self.bill.consumo_annuo_kwh = consumo * 12
                self.bill.consumo_totale_periodo = consumo
            elif consumo < 5000:  # Potrebbe essere bimestrale
                self.bill.consumo_totale_periodo = consumo
                self.bill.consumo_mensile_kwh = consumo / 2
                self.bill.consumo_annuo_kwh = consumo * 6
            else:  # Probabilmente annuo
                self.bill.consumo_annuo_kwh = consumo
                self.bill.consumo_mensile_kwh = consumo / 12
                self.bill.consumo_totale_periodo = consumo
        
        # Fasce orarie
        self.bill.consumo_f1 = self._extract_float(text, self.PATTERNS['fascia_f1'])
        self.bill.consumo_f2 = self._extract_float(text, self.PATTERNS['fascia_f2'])
        self.bill.consumo_f3 = self._extract_float(text, self.PATTERNS['fascia_f3'])
        
        # Se abbiamo le fasce, verifica consistenza
        if all([self.bill.consumo_f1, self.bill.consumo_f2, self.bill.consumo_f3]):
            totale_fasce = self.bill.consumo_f1 + self.bill.consumo_f2 + self.bill.consumo_f3
            if not consumo or abs(consumo - totale_fasce) < 10:
                self.bill.consumo_totale_periodo = totale_fasce
                self.bill.tipo_tariffa = 'trioraria'
    
    def _extract_power(self, text: str):
        """Estrae dati sulla potenza"""
        self.bill.potenza_impegnata_kw = self._extract_float(text, self.PATTERNS['potenza'])
        self.bill.potenza_max_prelevata_kw = self._extract_float(text, self.PATTERNS['potenza_max'])
        
        # Se disponibile = impegnata di solito
        if self.bill.potenza_impegnata_kw:
            self.bill.potenza_disponibile_kw = self.bill.potenza_impegnata_kw
    
    def _extract_costs(self, text: str):
        """Estrae tutti i costi"""
        self.bill.spesa_energia = self._extract_float(text, self.PATTERNS['spesa_energia'])
        self.bill.spesa_trasporto_gestione = self._extract_float(text, self.PATTERNS['spesa_trasporto'])
        self.bill.spesa_oneri_sistema = self._extract_float(text, self.PATTERNS['oneri_sistema'])
    
    def _extract_taxes(self, text: str):
        """Estrae imposte"""
        self.bill.accise = self._extract_float(text, self.PATTERNS['accise'])
        self.bill.iva = self._extract_float(text, self.PATTERNS['iva'])
    
    def _extract_totals(self, text: str):
        """Estrae totali"""
        self.bill.totale_bolletta = self._extract_float(text, self.PATTERNS['totale'])
        self.bill.totale_da_pagare = self.bill.totale_bolletta
    
    def _extract_contract_type(self, text: str):
        """Determina tipo di contratto"""
        # Tipo prezzo
        if re.search(self.PATTERNS['prezzo_fisso'], text):
            self.bill.tipo_prezzo = 'fisso'
        elif re.search(self.PATTERNS['prezzo_variabile'], text):
            self.bill.tipo_prezzo = 'variabile'
        
        # Tipo mercato
        if 'mercato libero' in text or 'offerta' in text:
            self.bill.tipo_mercato = 'libero'
        elif 'tutela' in text or 'maggior tutela' in text:
            self.bill.tipo_mercato = 'tutelato'
    
    def _calculate_derived_fields(self):
        """Calcola campi derivati dai dati estratti"""
        # Stima annua se mancante
        if not self.bill.consumo_annuo_kwh and self.bill.consumo_mensile_kwh:
            self.bill.consumo_annuo_kwh = self.bill.consumo_mensile_kwh * 12
        
        # Calcola prezzo medio kWh
        if self.bill.spesa_energia and self.bill.consumo_totale_periodo:
            self.bill.prezzo_energia_kwh = self.bill.spesa_energia / self.bill.consumo_totale_periodo
        
        if self.bill.totale_bolletta and self.bill.consumo_totale_periodo:
            self.bill.prezzo_medio_kwh = self.bill.totale_bolletta / self.bill.consumo_totale_periodo
        
        # Default se mancanti critici
        if not self.bill.consumo_annuo_kwh:
            # Stima basata su potenza se disponibile
            if self.bill.potenza_impegnata_kw:
                self.bill.consumo_annuo_kwh = self.bill.potenza_impegnata_kw * 900  # Euristica
            else:
                self.bill.consumo_annuo_kwh = 2700  # Media italiana famiglia
        
        if not self.bill.consumo_mensile_kwh:
            self.bill.consumo_mensile_kwh = self.bill.consumo_annuo_kwh / 12
        
        if not self.bill.potenza_impegnata_kw:
            self.bill.potenza_impegnata_kw = 3.0  # Standard residenziale
        
        # Subtotale (senza IVA)
        if self.bill.totale_bolletta and self.bill.iva:
            self.bill.subtotale = self.bill.totale_bolletta - self.bill.iva
    
    def _calculate_confidence(self):
        """Calcola confidence score basato su campi estratti"""
        # Campi critici (peso maggiore)
        critical_fields = [
            'fornitore', 'consumo_annuo_kwh', 'totale_bolletta',
            'potenza_impegnata_kw', 'tipo_prezzo'
        ]
        
        # Campi importanti
        important_fields = [
            'spesa_energia', 'spesa_trasporto_gestione', 'spesa_oneri_sistema',
            'accise', 'iva', 'periodo_fatturazione'
        ]
        
        # Campi opzionali
        optional_fields = [
            'consumo_f1', 'consumo_f2', 'consumo_f3',
            'potenza_max_prelevata_kw', 'numero_cliente'
        ]
        
        score = 0.0
        
        # Critical: 50% del score
        for field in critical_fields:
            if getattr(self.bill, field) is not None:
                score += 0.50 / len(critical_fields)
        
        # Important: 30% del score
        for field in important_fields:
            if getattr(self.bill, field) is not None:
                score += 0.30 / len(important_fields)
        
        # Optional: 20% del score
        for field in optional_fields:
            if getattr(self.bill, field) is not None:
                score += 0.20 / len(optional_fields)
        
        self.bill.confidence_score = round(score, 2)
        
        # Conta campi estratti
        all_fields = critical_fields + important_fields + optional_fields
        self.bill.campi_estratti = sum(1 for f in all_fields if getattr(self.bill, f) is not None)
        self.bill.campi_totali = len(all_fields)
    
    def _default_profile(self) -> Dict:
        """Profilo di default se parsing totalmente fallisce"""
        default = BillData(
            consumo_annuo_kwh=2700,
            consumo_mensile_kwh=225,
            potenza_impegnata_kw=3.0,
            totale_bolletta=50.0,
            confidence_score=0.0
        )
        return asdict(default)
    
    def get_summary(self) -> str:
        """Ritorna riassunto leggibile"""
        parts = []
        
        if self.bill.fornitore:
            parts.append(f"Fornitore: {self.bill.fornitore}")
        
        if self.bill.consumo_annuo_kwh:
            parts.append(f"Consumi: {self.bill.consumo_annuo_kwh:.0f} kWh/anno")
        
        if self.bill.totale_bolletta:
            parts.append(f"Costo: €{self.bill.totale_bolletta:.2f}")
        
        if self.bill.potenza_impegnata_kw:
            parts.append(f"Potenza: {self.bill.potenza_impegnata_kw} kW")
        
        if self.bill.tipo_prezzo:
            parts.append(f"Tipo: {self.bill.tipo_prezzo}")
        
        parts.append(f"Confidence: {self.bill.confidence_score*100:.0f}%")
        
        return " | ".join(parts)


# =============================================================================
# FUNZIONE DA USARE IN STREAMLIT
# =============================================================================

def parse_bill_enhanced(text: str) -> Dict:
    """
    Funzione wrapper per uso in Streamlit
    Sostituisce parse_bill_simple()
    
    Args:
        text: Testo estratto dalla bolletta
    
    Returns:
        Dict con tutti i campi estratti + backward compatibility
    """
    parser = EnhancedBillParser()
    result = parser.parse(text)
    
    # Aggiungi campi per backward compatibility con il codice esistente
    result['totale'] = result.get('totale_bolletta')
    result['consumo_kwh'] = result.get('consumo_mensile_kwh')
    
    return result


# =============================================================================
# TEST FUNCTION
# =============================================================================

if __name__ == "__main__":
    # Test con esempi
    sample_texts = [
        """
        ENEL ENERGIA S.p.A.
        Bolletta n. 123456789
        Cliente: 987654321
        
        Periodo: 01/10/2024 - 31/10/2024
        
        CONSUMI
        Energia attiva consumata: 250 kWh
        Fascia F1: 80 kWh
        Fascia F2: 90 kWh
        Fascia F3: 80 kWh
        
        Potenza impegnata: 3.0 kW
        Potenza massima prelevata: 2.8 kW
        
        DETTAGLIO IMPORTI
        Spesa per l'energia: €45.50
        Spesa per trasporto e gestione: €12.30
        Oneri di sistema: €8.20
        Accise: €3.45
        IVA 10%: €6.95
        
        TOTALE DA PAGARE: €76.40
        
        Contratto: Energia Casa Prezzo Fisso
        """,
        
        """
        ENI PLENITUDE
        Fattura periodo 15/09/2024 - 14/11/2024
        
        Consumo totale periodo: 450 kWh
        Potenza: 4.5 kW
        
        Spesa energia elettrica: €85.20
        Trasporto e distribuzione: €22.15
        Oneri generali: €15.80
        
        Subtotale: €123.15
        Accisa: €6.75
        IVA: €12.99
        
        Totale: €142.89
        
        Offerta: Link Luce Variabile
        """
    ]
    
    for i, text in enumerate(sample_texts, 1):
        print(f"\n{'='*80}")
        print(f"TEST SAMPLE {i}")
        print('='*80)
        
        parser = EnhancedBillParser()
        result = parser.parse(text)
        
        print(f"\n{parser.get_summary()}\n")
        
        print("DETTAGLI ESTRATTI:")
        for key, value in result.items():
            if value is not None and key not in ['campi_totali', 'campi_estratti']:
                print(f"  {key}: {value}")