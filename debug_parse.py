#!/usr/bin/env python3
"""
Script de debug para entender o parsing
"""
import os
from main import read_pdf_text, extract_lines

# Caminho para o PDF
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "Curriculum", "OrlandoKrause_EN (3).pdf")

def main():
    print("🔍 DEBUG DO PARSING")
    print("=" * 50)
    
    # Lê o PDF
    print(f"📖 Lendo PDF: {PDF_PATH}")
    text = read_pdf_text(PDF_PATH)
    print(f"   Texto extraído: {len(text)} caracteres")
    
    # Extrai linhas
    lines = extract_lines(text)
    print(f"   Linhas extraídas: {len(lines)}")
    
    # Mostra algumas linhas para debug
    print("\n📝 PRIMEIRAS 30 LINHAS:")
    print("-" * 30)
    for i, line in enumerate(lines[:30]):
        print(f"{i+1:2d}: {line}")
    
    # Procura por experiências
    print("\n💼 PROCURANDO POR EXPERIÊNCIAS:")
    print("-" * 30)
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ["software engineer", "architect", "senior", "paytrack", "senior sistemas", "quality assurance", "tester"]):
            print(f"{i+1:2d}: {line}")
    
    # Mostra todas as linhas para análise completa
    print("\n📋 TODAS AS LINHAS:")
    print("-" * 30)
    for i, line in enumerate(lines):
        print(f"{i+1:2d}: {line}")

if __name__ == "__main__":
    main()
