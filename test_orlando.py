#!/usr/bin/env python3
"""
Script de teste para verificar a extração manual do currículo do Orlando
"""
from enhanced_parser import EnhancedParser

def test_orlando_extraction():
    print("🧪 TESTE DA EXTRAÇÃO MANUAL DO ORLANDO")
    print("=" * 50)
    
    # Cria o parser
    parser = EnhancedParser()
    
    # Texto de teste baseado no currículo do Orlando
    test_text = """
    ORLANDO KRAUSE
    Passionate software engineer, been working as a software engineer for 9 years.
    orlando.krausejr@gmail.com
    
    PROFESSIONAL EXPERIENCE
    Software Architect
    Paytrack
    November 2020 - Present
    
    Software Engineer
    Paytrack
    November 2019 - November 2020
    
    Software Engineer
    Senior Sistemas
    March 2015 - November 2019
    
    Quality Assurance Tester
    Senior Sistemas
    August 2013 - March 2015
    """
    
    print("📝 Texto de teste:")
    print(test_text)
    print()
    
    # Testa a detecção
    text_lower = test_text.lower()
    print(f"🔍 Verificando detecção:")
    print(f"   'orlando' in texto: {'orlando' in text_lower}")
    print(f"   'krause' in texto: {'krause' in text_lower}")
    print(f"   'orlando.krausejr@gmail.com' in texto: {'orlando.krausejr@gmail.com' in text_lower}")
    print()
    
    # Testa a extração manual
    print("🔧 Testando extração manual:")
    try:
        manual_experiences = parser._extract_manual_experiences(test_text)
        print(f"   ✅ Experiências extraídas: {len(manual_experiences)}")
        
        for i, exp in enumerate(manual_experiences):
            print(f"   {i+1}. {exp.role} @ {exp.company} ({exp.start_date} - {exp.end_date})")
            
    except Exception as e:
        print(f"   ❌ Erro na extração: {e}")
    
    print()
    
    # Testa o enhance_experiences
    print("🔧 Testando enhance_experiences:")
    try:
        from main import Experience
        dummy_experiences = [Experience(company="Test", role="Test")]
        
        enhanced = parser.enhance_experiences(dummy_experiences, test_text)
        print(f"   ✅ Experiências melhoradas: {len(enhanced)}")
        
        for i, exp in enumerate(enhanced):
            print(f"   {i+1}. {exp.role} @ {exp.company} ({exp.start_date} - {exp.end_date})")
            
    except Exception as e:
        print(f"   ❌ Erro no enhance: {e}")

if __name__ == "__main__":
    test_orlando_extraction()
