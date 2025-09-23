#!/usr/bin/env python3
"""
Script de teste para demonstrar as melhorias do parser aprimorado
"""

import json
import os
from enhanced_parser import EnhancedParser
from main import read_pdf_text

def test_enhanced_parser():
    """Testa o parser melhorado com um CV de exemplo"""
    
    # Verifica se existe um CV para testar
    source_dir = r"C:\Users\joao.miguel\Documents\Curriculum"
    if not os.path.exists(source_dir):
        print(f"❌ Diretório de CVs não encontrado: {source_dir}")
        return
    
    # Lista PDFs disponíveis
    pdfs = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    if not pdfs:
        print(f"❌ Nenhum PDF encontrado em: {source_dir}")
        return
    
    print(f"📁 PDFs encontrados: {len(pdfs)}")
    for pdf in pdfs[:3]:  # Mostra apenas os primeiros 3
        print(f"   - {pdf}")
    
    # Testa com o primeiro PDF
    test_pdf = os.path.join(source_dir, pdfs[0])
    print(f"\n🔍 Testando com: {pdfs[0]}")
    
    try:
        # Lê o PDF
        print("📖 Lendo PDF...")
        raw_text = read_pdf_text(test_pdf)
        print(f"   Texto extraído: {len(raw_text)} caracteres")
        
        # Testa o parser melhorado
        print("🚀 Executando parser melhorado...")
        enhanced_parser = EnhancedParser()
        result = enhanced_parser.parse_enhanced(raw_text)
        
        # Mostra resultados
        print("\n✅ RESULTADOS DO PARSER MELHORADO:")
        print("=" * 50)
        
        # Informações básicas
        print(f"👤 Nome: {result.candidate.full_name or 'Não encontrado'}")
        print(f"📧 Emails: {len(result.candidate.emails)} encontrados")
        print(f"📱 Telefones: {len(result.candidate.phones)} encontrados")
        
        # Localização
        if result.candidate.location:
            loc = result.candidate.location
            location_str = []
            if loc.city: location_str.append(loc.city)
            if loc.state: location_str.append(loc.state)
            if loc.country: location_str.append(loc.country)
            print(f"📍 Localização: {', '.join(location_str) if location_str else 'Não encontrada'}")
        
        # Links
        if result.candidate.links:
            links = result.candidate.links
            if links.linkedin: print(f"🔗 LinkedIn: {links.linkedin}")
            if links.github: print(f"🐙 GitHub: {links.github}")
            if links.portfolio: print(f"💼 Portfolio: {links.portfolio}")
        
        # Resumo
        if result.summary:
            print(f"\n📝 Resumo/Objetivo:")
            print(f"   {result.summary[:200]}{'...' if len(result.summary) > 200 else ''}")
        
        # Skills
        if result.skills:
            print(f"\n🛠️  Skills ({len(result.skills)} encontradas):")
            for skill in result.skills[:10]:  # Mostra apenas as primeiras 10
                level_str = f" ({skill.level})" if skill.level != "na" else ""
                print(f"   - {skill.name}{level_str} [conf: {skill.confidence}]")
        
        # Idiomas
        if result.languages:
            print(f"\n🌍 Idiomas ({len(result.languages)} encontrados):")
            for lang in result.languages:
                level_str = f" - {lang.level_cefr}" if lang.level_cefr else ""
                print(f"   - {lang.name}{level_str} [conf: {lang.confidence}]")
        
        # Experiências
        if result.experiences:
            print(f"\n💼 Experiências ({len(result.experiences)} encontradas):")
            for i, exp in enumerate(result.experiences[:3], 1):  # Mostra apenas as primeiras 3
                print(f"   {i}. {exp.role or 'Cargo não especificado'} @ {exp.company or 'Empresa não especificada'}")
                if exp.start_date or exp.end_date:
                    dates = []
                    if exp.start_date: dates.append(f"desde {exp.start_date}")
                    if exp.end_date: dates.append(f"até {exp.end_date}")
                    elif exp.is_current: dates.append("atual")
                    print(f"      Período: {' - '.join(dates)}")
                
                if exp.achievements:
                    print(f"      Conquistas: {len(exp.achievements)} encontradas")
                    for achievement in exp.achievements[:2]:  # Mostra apenas as primeiras 2
                        print(f"        • {achievement[:100]}{'...' if len(achievement) > 100 else ''}")
                
                if exp.tech_stack:
                    print(f"      Tech Stack: {', '.join(exp.tech_stack[:5])}{'...' if len(exp.tech_stack) > 5 else ''}")
        
        # Educação
        if result.education:
            print(f"\n🎓 Educação ({len(result.education)} encontrada):")
            for edu in result.education:
                inst_str = f" - {edu.institution}" if edu.institution else ""
                print(f"   - {edu.degree or 'Grau não especificado'}{inst_str}")
                if edu.start_date or edu.end_date:
                    dates = []
                    if edu.start_date: dates.append(f"desde {edu.start_date}")
                    if edu.end_date: dates.append(f"até {edu.end_date}")
                    print(f"      Período: {' - '.join(dates)}")
        
        # Certificações
        if result.certifications:
            print(f"\n🏆 Certificações ({len(result.certifications)} encontradas):")
            for cert in result.certifications[:5]:  # Mostra apenas as primeiras 5
                issuer_str = f" ({cert.get('issuer', 'N/A')})" if cert.get('issuer') else ""
                date_str = f" - {cert.get('date', 'N/A')}" if cert.get('date') else ""
                print(f"   - {cert['name']}{issuer_str}{date_str}")
        
        # Projetos (do meta)
        if result.meta.get("projects"):
            projects = result.meta["projects"]
            print(f"\n🚀 Projetos ({len(projects)} encontrados):")
            for project in projects[:3]:  # Mostra apenas os primeiros 3
                print(f"   - {project['name']}")
                if project['technologies']:
                    tech_str = ', '.join(project['technologies'][:5])
                    print(f"     Tech: {tech_str}{'...' if len(project['technologies']) > 5 else ''}")
        
        # Conquistas gerais (do meta)
        if result.meta.get("achievements"):
            achievements = result.meta["achievements"]
            print(f"\n🏅 Conquistas Gerais ({len(achievements)} encontradas):")
            for achievement in achievements[:3]:  # Mostra apenas as primeiras 3
                print(f"   • {achievement[:100]}{'...' if len(achievement) > 100 else ''}")
        
        # Meta informações
        print(f"\n📊 Meta informações:")
        print(f"   - Versão do parser: {result.meta.get('parser_version', 'N/A')}")
        print(f"   - Tamanho do texto: {result.meta.get('raw_len', 'N/A')} caracteres")
        print(f"   - Confiança geral: {result.meta.get('confidence', 'N/A')}")
        
        # Salva resultado em arquivo
        output_file = "output/teste_enhanced_parser.json"
        os.makedirs("output", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Resultado salvo em: {output_file}")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()

def compare_parsers():
    """Compara o parser original com o melhorado"""
    print("\n🔄 COMPARAÇÃO DE PARSERS")
    print("=" * 50)
    
    source_dir = r"C:\Users\joao.miguel\Documents\Curriculum"
    if not os.path.exists(source_dir):
        print("❌ Diretório de CVs não encontrado")
        return
    
    pdfs = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    if not pdfs:
        print("❌ Nenhum PDF encontrado")
        return
    
    test_pdf = os.path.join(source_dir, pdfs[0])
    
    try:
        # Parser original
        from main import extract_all
        raw_text = read_pdf_text(test_pdf)
        
        print("📊 PARSER ORIGINAL:")
        result_original = extract_all(raw_text)
        print(f"   - Skills: {len(result_original.skills)}")
        print(f"   - Experiências: {len(result_original.experiences)}")
        print(f"   - Educação: {len(result_original.education)}")
        print(f"   - Certificações: {len(result_original.certifications)}")
        
        # Parser melhorado
        print("\n📊 PARSER MELHORADO:")
        enhanced_parser = EnhancedParser()
        result_enhanced = enhanced_parser.parse_enhanced(raw_text)
        print(f"   - Skills: {len(result_enhanced.skills)}")
        print(f"   - Experiências: {len(result_enhanced.experiences)}")
        print(f"   - Educação: {len(result_enhanced.education)}")
        print(f"   - Certificações: {len(result_enhanced.certifications)}")
        print(f"   - Resumo: {'Sim' if result_enhanced.summary else 'Não'}")
        print(f"   - Projetos: {len(result_enhanced.meta.get('projects', []))}")
        print(f"   - Conquistas: {len(result_enhanced.meta.get('achievements', []))}")
        
        # Calcula melhoria
        skills_improvement = len(result_enhanced.skills) - len(result_original.skills)
        exp_improvement = len(result_enhanced.experiences) - len(result_original.experiences)
        
        print(f"\n📈 MELHORIAS:")
        skills_percent = (skills_improvement/len(result_original.skills)*100) if len(result_original.skills) > 0 else 0
        exp_percent = (exp_improvement/len(result_original.experiences)*100) if len(result_original.experiences) > 0 else 0
        print(f"   - Skills: +{skills_improvement} ({skills_percent:.1f}%)")
        print(f"   - Experiências: +{exp_improvement} ({exp_percent:.1f}%)")
        print(f"   - Novas funcionalidades: Resumo, Projetos, Conquistas, Tech Stack por experiência")
        
    except Exception as e:
        print(f"❌ Erro na comparação: {str(e)}")

if __name__ == "__main__":
    print("🚀 TESTE DO PARSER MELHORADO")
    print("=" * 50)
    
    # Testa o parser melhorado
    test_enhanced_parser()
    
    # Compara com o parser original
    compare_parsers()
    
    print("\n✨ Teste concluído!")
