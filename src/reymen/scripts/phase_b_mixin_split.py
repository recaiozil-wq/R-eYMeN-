"""Phase B: ReYMeNCLI class'ını 6 mixin'e böl.

Her mixin dosyası: reymen/sistem/cli_mixin_*.py
Kaynak: cli_main.py içindeki ReYMeNCLI class'ı (185 metot)
"""

import ast
import os
import re
import shutil

ROOT = r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan"
MAIN_PATH = os.path.join(ROOT, "reymen", "sistem", "cli_main.py")
MIXIN_DIR = os.path.join(ROOT, "reymen", "sistem")

# Metot kategorileri
CATEGORIES = {
    "display": {
        "name": "MixinDisplay",
        "desc": "UI/ekran/çıktı formatlama metotları",
        "patterns": [
            "_format_", "_print_", "_render_", "_show_", "_build_",
            "_status_bar_", "_tui_", "_scrollback_", "_spinner_",
            "_console_", "_rich_", "_color_", "_table_",
            "_get_tui_", "_apply_tui_", "_register_extra_",
            "_audio_level_", "_get_extra_",
            # spesifik isimler
            "_invalidate", "_force_full_redraw",
            "_clear_prompt_toolkit_screen",
            "_recover_after_resize", "_schedule_resize_recovery",
            "_get_status_bar_snapshot",
            "_trim_status_bar_text",
            "_get_status_bar_fragments",
            "_build_context_bar",
            "_expand_paste_references",
            "_print_exit_summary",
            "_prefill_input_buffer",
        ],
        "exclude": []
    },
    "stream": {
        "name": "MixinStream",
        "desc": "Stream/akış metotları",
        "patterns": [
            "_stream_", "_flush_", "_emit_", "_reset_stream",
            "_on_thinking", "_on_reasoning",
            "_current_reasoning", "_emit_reasoning",
            "_flush_reasoning", "_close_reasoning",
            "_stream_reasoning",
        ],
        "exclude": []
    },
    "voice": {
        "name": "MixinVoice",
        "desc": "Ses/voice metotları",
        "patterns": [
            "_voice_", "set_voice_",
        ],
        "exclude": []
    },
    "approval": {
        "name": "MixinApproval",
        "desc": "Onay/güvenlik metotları",
        "patterns": [
            "_approval_", "_sudo_", "_secret_", "_clarify_callback",
            "_capture_modal", "_restore_modal", "_submit_secret",
            "_cancel_secret", "_clear_secret",
        ],
        "exclude": []
    },
    "commands": {
        "name": "MixinCommands",
        "desc": "Komut işleyiciler",
        "patterns": [
            "_handle_", "process_command",
            "show_help", "show_tools", "show_toolsets",
            "show_config", "show_history", "show_banner",
            "new_session", "save_conversation",
            "retry_last", "undo_last", "chat", "run",
            "_show_", "show_",
            "_toggle_", "_transfer_", "_is_session_",
            "_manual_compress",
            "_confirm_", "_split_destructive",
            "_reload_", "_check_config_",
            "_try_launch_", "_try_attach_",
            "_preprocess_images_",
            "_open_external_editor",
            "_write_osc52", "_recover_terminal",
            "_notify_session_boundary",
            "_consume_pending_",
            "_run_curses_", "_prompt_text_",
            "_submit_slash_", "_normalize_slash_",
            "_get_slash_confirm_",
            "_open_model_", "_close_model_",
            "_compute_model_", "_apply_model_",
            "_handle_model_",
            "_handle_codex_", "_should_handle_",
            "_output_console",
            "_resolve_personality_",
            "_slow_command_", "_command_spinner_",
            "_busy_command",
            "_display_resumed_",
            "_on_tool_",
            "_maybe_continue_goal_",
        ],
        "exclude": ["_show_security_advisories", "_show_status", "_show_session_status",
                     "_show_voice_status", "_show_gateway_status", "_show_usage", "_show_insights",
                     "_print_exit_summary"]
    },
}

def categorize(method_name):
    """Bir metodun hangi kategoriye ait olduğunu belirle."""
    for cat_key, cat_info in CATEGORIES.items():
        if method_name in cat_info.get("exclude", []):
            continue
        for pat in cat_info["patterns"]:
            if method_name == pat or method_name.startswith(pat):
                return cat_key
    return "core"  # default

def extract_method_source(main_path, method_name):
    """Ast kullanarak bir metodun kaynak kodunu çıkar."""
    with open(main_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'ReYMeNCLI':
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    start = item.lineno - 1
                    end = item.end_lineno
                    return ''.join(lines[start:end])
    return None


def main():
    # 1) Tüm metodları parse et
    with open(MAIN_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    all_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'ReYMeNCLI':
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cat = categorize(item.name)
                    all_methods.append((item.name, cat, item.lineno, item.end_lineno))
            break
    
    print(f"Toplam metot: {len(all_methods)}")
    
    # Kategori bazında say
    cat_counts = {}
    for name, cat, _, _ in all_methods:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    for cat in sorted(cat_counts.keys()):
        cat_name = CATEGORIES.get(cat, {}).get("name", f"Mixin{cat.capitalize()}")
        desc = CATEGORIES.get(cat, {}).get("desc", "")
        print(f"  {cat_name:25s} ({cat:15s}): {cat_counts[cat]:3d} metot  {desc}")
    
    # 2) Her kategori için mixin dosyası oluştur
    import_line = "from reymen.sistem.cli_main import ReYMeNCLI"
    
    # Kategori listesi
    all_cats = list(CATEGORIES.keys()) + ["core"]
    
    # core kategorisi için dict
    CATEGORIES["core"] = {
        "name": "MixinCore",
        "desc": "Ana/kalan metotlar",
        "patterns": [],
        "exclude": []
    }
    
    mixin_imports = []
    mixin_names = []
    
    for cat_key in all_cats:
        cat_info = CATEGORIES[cat_key]
        cat_methods = [(n, c, s, e) for n, c, s, e in all_methods if c == cat_key]
        
        if not cat_methods:
            print(f"  ⚠️  {cat_info['name']}: boş, oluşturulmayacak")
            continue
        
        mixin_name = cat_info["name"]
        file_name = f"cli_mixin_{cat_key}.py"
        file_path = os.path.join(MIXIN_DIR, file_name)
        
        # Mixin içeriğini oluştur
        mixin_lines = [
            f'"""ReYMeNCLI {mixin_name} — {cat_info["desc"]}."""',
            '',
            '',
            f'class {mixin_name}:',
            f'    """ReYMeNCLI {cat_info["desc"]}."""',
            '',
        ]
        
        # Her metodun kaynağını al ve ekle
        with open(MAIN_PATH, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        for meth_name, _, start, end in sorted(cat_methods, key=lambda x: x[2]):
            source = ''.join(all_lines[start-1:end])
            if source:
                # İlk satırdaki decorator'ları da al (varsa)
                actual_start = start - 1
                for i in range(start - 2, max(0, start - 5), -1):
                    stripped = all_lines[i].strip()
                    if stripped.startswith('@') or stripped == '':
                        actual_start = i
                    else:
                        break
                source = ''.join(all_lines[actual_start:end])
                mixin_lines.append(source)
                mixin_lines.append('')
        
        content_out = '\n'.join(mixin_lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_out)
        
        print(f"  ✅ {file_name} oluşturuldu ({len(cat_methods)} metot)")
        mixin_imports.append(f'from reymen.sistem.{file_name.replace(".py","")} import {mixin_name}')
        mixin_names.append(mixin_name)
    
    # 3) cli_main.py'yi güncelle
    # Import'ları ekle
    import_block = '\n'.join(mixin_imports)
    
    # Class tanımını bul ve değiştir
    with open(MAIN_PATH, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Eski class ReYMeNCLI satırını mixin miraslı hale getir
    class_line_pattern = r'^class ReYMeNCLI\([^)]*\):'
    match = re.search(class_line_pattern, main_content, re.MULTILINE)
    
    if match:
        old_class_line = match.group(0)
        inheritance = ', '.join(mixin_names)
        new_class_line = f'class ReYMeNCLI({inheritance}):'
        
        # Import'ları en başa ekle (ilk import bloğundan sonra)
        lines = main_content.split('\n')
        
        # class tanımını değiştir
        for i, line in enumerate(lines):
            if line.rstrip() == old_class_line.rstrip():
                lines[i] = new_class_line
                break
        
        # Import'ları ekle (en üstteki __init__ dışı import'lardan sonra)
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                last_import = i
        
        insert_pos = last_import + 1
        for imp in reversed(mixin_imports):
            lines.insert(insert_pos, imp)
        
        main_content = '\n'.join(lines)
        
        with open(MAIN_PATH, 'w', encoding='utf-8') as f:
            f.write(main_content)
        
        print(f"\n✅ cli_main.py güncellendi: {old_class_line} → {new_class_line}")
        print(f"   {len(mixin_imports)} import eklendi")
    
    print("\n✅ Phase B tamam!")


if __name__ == '__main__':
    main()
