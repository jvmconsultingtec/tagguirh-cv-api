#!/usr/bin/env python3
"""
Script de debug para testar a validação de empresas
"""

from enhanced_parser import EnhancedParser

def test_company_validation():
    """Testa a validação de empresas"""
    parser = EnhancedParser()
    
    # Testa empresas que NÃO deveriam ser válidas
    invalid_companies = [
        "Metodologias ágeis",
        "Redshift, React e Flutter", 
        "Blumenau",
        "React",
        "Java",
        "Spring",
        "Scrum",
        "Kanban",
        "Desenvolvimento de Software",
        "Team Leader",
        "Diretor de Tecnologia"
    ]
    
    print("🔍 TESTANDO VALIDAÇÃO DE EMPRESAS")
    print("=" * 50)
    
    for company in invalid_companies:
        is_valid = parser._is_valid_company(company)
        cleaned = parser._clean_company_name(company)
        print(f"❌ '{company}' -> Válida: {is_valid}, Limpa: '{cleaned}'")
    
    # Testa empresas que DEVERIAM ser válidas
    valid_companies = [
        "Paytrack",
        "Senior Sistemas",
        "Benner Sistemas",
        "GOVBR",
        "Social NT",
        "Cetelbras Educacional",
        "Dock",
        "Caylent",
        "Redshift",
        "PedidosWeb",
        "INPG",
        "FURB"
    ]
    
    print("\n✅ TESTANDO EMPRESAS VÁLIDAS")
    print("=" * 50)
    
    for company in valid_companies:
        is_valid = parser._is_valid_company(company)
        cleaned = parser._clean_company_name(company)
        print(f"✅ '{company}' -> Válida: {is_valid}, Limpa: '{cleaned}'")

if __name__ == "__main__":
    test_company_validation()
