import re
import sys
import argparse
import os

from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(1)

directory = Path(sys.argv[1])


with open(directory, 'r', encoding='utf-8') as f:
    content = f.read()

class Token:
    def __init__(self, type, value, line):
        self.type = type
        self.value = value
        self.line = line

token_specification = [
    ('CAST',       r'<\s*[a-zA-Z_][\w.]*\s*>'), 
    ('OPERATOR', r'[\+\-\*/%]'), 
    ('TYPE',       r'gds\.[a-zA-Z_]\w*'), 
    ('KEYWORD',    r'\bgds\b|\breturn\b'),
    ('ID_HOOK',    r'\$[a-zA-Z_]\w*'),
    ('ID',         r'[a-zA-Z_]\w*'),
    ('OP',         r'[=().,{}]'),                                   
    ('STRING',     r'"[^"]*"'),                  
    ('NUMBER',     r'0x[0-9a-fA-F]+|\d+(\.\d+)?'),             
    ('SKIP',       r'[ \t\n]+'),                 
    ('MISMATCH',   r'.'),                        
]

def preprocess_source(code):
    code = re.sub(r'//.*', '', code)
    return code

def tokenize(code):
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    tokens = []
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        current_line = code.count('\n', 0, mo.start()) + 1
        if kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f'FATAL: Unexpected character "{value}" at line {current_line}')
        tokens.append(Token(kind, value, current_line))
    return tokens
print(f"Tokenizing {directory}...")
cleaned = preprocess_source(content)
tokens = tokenize(cleaned)
print("Tokenizing done")

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected_type=None):
        token = self.peek()
        if expected_type and token.type != expected_type:
            raise Exception(f"Expected {expected_type}, got {token.type}")
        self.pos += 1
        return token

    def parse_program(self):
        self.eat('KEYWORD')
        self.eat('OP')
        functions = []
        global_vars = []
        hook_configs = {}
        while self.peek() and self.peek().type != 'ID_HOOK' and self.peek().value != '}':
            token = self.peek()
            if token.value == 'define':
                global_vars.append(self.parse_define())
            elif token.type == 'ID':
                global_vars.append(self.parse_global_assignment())
            else:
                self.eat()
        while self.peek() and self.peek().type == 'ID_HOOK':
            func = self.parse_function()
            functions.append(func)
        for func in functions:
            if func['name'] == '$onLoad':
                body_text = " ".join([t['value'] for t in func['body']])
                hooks = re.findall(r'gds\s*\.\s*hook\s*\(\s*"[^"]+"\s*,\s*\$(\w+)\s*,\s*true\s*\)', body_text)
                for h in hooks:
                    hook_configs[h] = True
        self.eat('OP')
        return {"type": "Program", "global_vars": global_vars, "body": functions, "hook_configs": hook_configs}
    def parse_define(self):
        self.eat()
        name = self.eat('ID').value
        value = self.eat().value
        return {"type": "Define", "name": name, "value": value}

    def parse_global_assignment(self):
        name = self.eat('ID').value
        self.eat('OP')
        value = self.eat().value
        return {"type": "GlobalVar", "name": name, "value": value}

    def parse_function(self):
        name = self.eat('ID_HOOK').value
        self.eat('OP') # (
    
        params = []
        while self.peek() and self.peek().value != ')':
            p_type = self.eat('TYPE').value
            p_name = None
            if self.peek() and self.peek().type == 'ID':
                p_name = self.eat('ID').value
            params.append({'type': p_type, 'name': p_name})
            if self.peek() and self.peek().value == ',':
                self.eat('OP')
            
        self.eat('OP') # )
        self.eat('OP') # {
    
        body = []
        return_type = "gds.void"
        while self.peek() and self.peek().value != '}':
            stmt = self.parse_statement()
            body.append(stmt)
            val = stmt['value'].strip()
            
            if val.startswith('return'):
                if '<' in val and '>' in val:
                    match = re.search(r'<([^>]+)>', val)
                    if match:
                        t = match.group(1).strip()
                        return_type = t if t.startswith("gds.") else f"gds.{t}"
                elif '"' in val:
                    return_type = "gds.string"
                elif re.search(r'\b(true|false)\b', val):
                    return_type = "gds.bool"
                elif re.search(r'\b\d+\b', val):
                    if return_type == "gds.void":
                        return_type = "gds.int"
                else:
                    return_type = "gds.voidptr"
        self.eat('OP') # }
        return {
        "type": "Function", 
        "name": name, 
        "params": params, 
        "body": body, 
        "return_type": return_type
        }   

    def parse_statement(self):
        token = self.eat()
        instruction = [token]
        while self.peek() and self.peek().line == token.line:
            instruction.append(self.eat())
        combined_value = " ".join([t.value for t in instruction])
        return {"type": "Statement", "value": combined_value, "line": token.line}
print("Parsing...")
parser = Parser(tokens)
ast = parser.parse_program()
print("Parsing done")
class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.symbol_table = set()
        self.valid_types = {'gds.void', 'gds.bool', 'gds.int', 'gds.char_ptr', 'gds.string', 'gds.layer', 'gds.win_size', 'gds.javavm', 'bool'}
        self.keywords = {'return', 'true', 'false', 'gds', 'self', 'window', 'bool', 'string', 'win_size', 'width', 'height', 'x', 'y'}
        self.function_registry = {
            'gds.spriteWithFrameName': 1,
            'gds.createSprite': 1,
            'gds.addChild': 2,
            'gds.point': 2,
            'gds.createMenu': 0,
            'gds.hook': 3,
            'memberByOffset': 1,
            'gds.patch': 2,
            'gds.getJavaVM': 0,
        }

        

    def error(self, message, line):
        raise RuntimeError(f"Compilation Error at line {line}: {message}")

    def analyze(self):
        if not self.ast or self.ast.get('type') != 'Program':
            raise RuntimeError(f"FATAL: Code must be wrapped inside a gds {{}} block.")
        self.defined_functions = set()
        for func in self.ast['body']:
            name = func['name']
            clean_name = name[1:] if name.startswith('$') else name
            self.defined_functions.add(clean_name)
        for func in self.ast['body']:
            self.current_scope = set()
            for p in func['params']:
                if p['name']:
                    self.current_scope.add(p['name'])
                if p['type'] not in self.valid_types:
                    self.error(f"Unknown type '{p['type']}'", func.get('line', 'unknown'))
            self.check_body(func['body'], func.get('line', 'unknown'))

    def check_body(self, statements, func_line):
        for stmt in statements:
            val = stmt['value']
            line = stmt['line']
            if '=' in val:
                parts = val.split('=', 1)
                var_name = parts[0].strip()
                usage_part = parts[1]
                self.check_usage(usage_part, line)
                self.current_scope.add(var_name)
            else:
                self.check_usage(val, line)
        for func_name, count in self.function_registry.items():
                if func_name in val:
                    args_part = re.search(rf'{re.escape(func_name)}\s*\((.*?)\)', val)
                    if args_part:
                        args = [a for a in args_part.group(1).split(',') if a.strip()]
                        if len(args) != count:
                            self.error(f"'{func_name}' expects {count} arguments, got {len(args)}", line)
        cast_match = re.search(r'<([\w.]+)>\s*(\w+)', val)
        if cast_match:
            cast_type, cast_val = cast_match.groups()
            if f"gds.{cast_type}" not in self.valid_types and cast_type not in self.valid_types:
                self.error(f"Cast to unknown type '<{cast_type}>'", line)
            if cast_type == 'gds.string' and cast_val in ['true', 'false']:
                self.error(f"Invalid C-style cast: Cannot cast boolean '{cast_val}' to string", line)

    def check_usage(self, text, line):
        if re.search(r'\b0x\b(?![0-9a-fA-F])', text):
            self.error("Invalid hex literal: '0x'", line)
        clean_text = re.sub(r'"[^"]*"', ' ', text)
        clean_text = re.sub(r'\b0x[0-9a-fA-F]+\b', ' ', clean_text)
        words = re.findall(r'\$?[a-zA-Z_]\w*', clean_text)
        for full_word in words:
            base_word = full_word.split('.')[0]
            clean_word = base_word[1:] if base_word.startswith('$') else base_word
            if clean_word in self.keywords: continue
            if any(clean_word in f for f in self.function_registry): continue
            if clean_word.endswith('_H'):
                if clean_word[:-2] in self.defined_functions:
                    continue
            if clean_word not in self.current_scope and clean_word not in self.defined_functions:
                self.error(f"Undeclared identifier '{base_word}'", line)

print("Analyzing...")
analyzer = SemanticAnalyzer(ast)
try:
    analyzer.analyze()
    print("Analysis done. No errors found.")
except RuntimeError as e:
    print(e)
    sys.exit(1)
def generate_cpp(ast):
    type_map = {
        'gds.void': 'void',
        'gds.voidptr': 'void*',
        'gds.bool': 'bool',
        'gds.int': 'int',
        'gds.char_ptr': 'const char*',
        'gds.string': 'std::string'
    }
    output = []
    uses_string = False
    uses_mbo = False
    for func in ast['body']:
        if func.get('return_type') == 'gds.string' or \
           any(p['type'] == 'gds.string' for p in func['params']) or \
           any(t['type'] == 'STRING' for t in func['body'] if 'type' in t):
            uses_string = True
            break
    for func in ast['body']:
        if any("memberByOffset" in stmt['value'] for stmt in func['body']):
            uses_mbo = True
            break
    
    output.append("#include \"include/include.h\"")

    if uses_string:
        output.append("#include <string>")

    output.append("\n")

    if uses_mbo:
        output.append("""#define MEMBER_BY_OFFSET(type, var, offset) \\
    (*reinterpret_cast<type*>(reinterpret_cast<uintptr_t>(var) + static_cast<uintptr_t>(offset)))\n""")

    for glob in ast.get('global_vars', []):
        if glob['type'] == 'Define':
            output.append(f"#define {glob['name']} {glob['value']}")
        elif glob['type'] == 'GlobalVar':
            val = glob['value']
            cpp_type = "bool" if val in ['true', 'false'] else "int"
            output.append(f"{cpp_type} {glob['name']} = {val};")

    if ast.get('global_vars'):
        output.append("")

    hook_configs = ast.get('hook_configs', {})
    for func in ast['body']:
        raw_name = func['name'] 
        clean_name = raw_name[1:]
        params_str = format_params(func['params'])
        gds_ret_type = func.get('return_type', 'gds.voidptr')
        cpp_ret_type = type_map.get(gds_ret_type, 'void*')
        if raw_name == '$onLoad':
            output.append("JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {")
            output.append(translate_statements(func['body']))
            output.append("    return JNI_VERSION_1_6;")
            output.append("}\n")
            continue
        output.append(f"{cpp_ret_type} (*{clean_name})({params_str});")
        output.append(f"{cpp_ret_type} {clean_name}_H({params_str}) {{")
        if clean_name in hook_configs:
            param_names = [p['name'] for p in func['params'] if p['name']]
            names_joined = ", ".join(param_names)
            output.append(f"    {clean_name}({names_joined});")
        output.append(translate_statements(func['body']))
        output.append("}\n")
        
    return "\n".join(output)

def translate_statements(statements):
    def clean_coords(text):
        text = text.strip()
        text = re.sub(r'(\w+)\.position\.([xy])', r'\1->getPosition().\2', text)
        text = re.sub(r'(\w+)\.position(?!\.)', r'\1->getPosition()', text)
        text = text.replace("gds.win_size", "CCDirector::sharedDirector()->getWinSize()")
        text = text.replace(" . ", ".")
        return text
    cpp_lines = []
    raw_text_body = " ".join([t['value'] for t in statements])
    patterns = [
        ('winsize', r'(\w+)\s*=\s*gds\s*\.\s*win_size'),
        ('get_javavm', r'(\w+)\s*=\s*gds\s*\.\s*getJavaVM()'),
        ('sprite_frame', r'(\w+)\s*=\s*gds\s*\.\s*spriteWithFrameName\s*\(\s*"([^"]+)"\s*\)'),
        ('sprite_create', r'(\w+)\s*=\s*gds\s*\.\s*createSprite\s*\(\s*"([^"]+)"\s*\)'),
        ('anchor', r'(\w+)\s*\.\s*anchor\s*=\s*gds\s*\.\s*point\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)'),
        ('position', r'(\w+)\s*\.\s*position\s*=\s*gds\s*\.\s*point\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)'),
        ('add_child', r'gds\s*\.\s*addChild\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)'),
        ('speed', r'gds\s*\.\s*speed\s*=\s*((\d+(\.\d*)?|\.\d+))[fF]?'),
        ('hook', r'gds\s*\.\s*hook\s*\(\s*"([^"]+)"\s*,\s*\$(\w+)\s*,\s*(\w+)\s*\)'),
        ('patch', r'gds\s*\.\s*patch\s*\(\s*([^,]+)\s*,\s*"([^"]+)"\s*\)'),
        ('return_cast', r'return\s+<(?P<type>[\w.]*)>\s*(?P<val>[^;}\s]+)'),
        ('member_offset', r'(\w+)\s*=\s*(?:<(?P<mem_type>[\w.]*)>)?\s*(?P<obj>\w+)\s*\.\s*memberByOffset\s*\(\s*(?P<offset>[^)]+)\s*\)'),
        ('return_stmt', r'\breturn\s+(?P<ret_val>.*?)(?=[;]|$)'),
        ('menu_create', r'(\w+)\s*=\s*gds\s*\.\s*createMenu\s*\(\s*\)'),
        ('pos_getter', r'(\w+)\s*\.\s*position(\s*\.\s*[xy])?'),
        ('menu_align', r'(\w+)\s*\.\s*alignment\s*=\s*"([^"]+)"'),
        ('assignment', r'(?P<var>\w+)\s*=\s*(?P<expr>.*?)(?=[;]|\s\w+\s*=|$)'),
    ]

    master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in patterns)
    patch_buffer = []
    matches = list(re.finditer(master_regex, raw_text_body))

    for i, match in enumerate(matches):
        kind = match.lastgroup
        matched_text = match.group(kind)
        
        if kind == 'winsize':
            var_name = match.group('winsize').split('=')[0].strip()
            cpp_lines.append(f'    auto {var_name} = CCDirector::sharedDirector()->getWinSize();')

        if kind == 'get_javavm':
            var_name = match.group('get_javavm').split('=')[0].strip()
            cpp_lines.append(f'    auto {var_name} = cocos2d::JniHelper::getJavaVM();')
        
        elif kind == 'sprite_frame':
            m = re.search(r'(\w+)\s*=\s*gds\s*\.\s*spriteWithFrameName\s*\(\s*"([^"]+)"\s*\)', match.group('sprite_frame'))
            cpp_lines.append(f'    auto {m.group(1)} = CCSprite::createWithSpriteFrameName("{m.group(2)}");')
        elif kind == 'sprite_create':
            pattern = r'(\w+)\s*=\s*gds\s*\.\s*createSprite\s*\(\s*"([^"]+)"\s*\)'
            m = re.search(pattern, match.group('sprite_create'))
            if m:
                cpp_lines.append(f'    auto {m.group(1)} = CCSprite::create("{m.group(2)}");')
        elif kind == 'menu_create':
            var_name = match.group('menu_create').split('=')[0].strip()
            cpp_lines.append(f'    auto {var_name} = CCMenu::create();')
        elif kind == 'pos_getter':
            m = re.search(r'(\w+)\s*\.\s*position', matched_text)
            if m:
                var_name = m.group(1)
                cpp_lines.append(f'    {var_name}->getPosition()')
        elif kind == 'position' or kind == 'anchor':
            pattern = r'(\w+)\s*\.\s*(?:position|anchor)\s*=\s*gds\s*\.\s*point\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)'
            m = re.search(pattern, matched_text)
            if m:
                var_name = m.group(1)
                raw_x, raw_y = m.group(2), m.group(3)
                clean_x = clean_coords(raw_x)
                clean_y = clean_coords(raw_y)
                func = "setPosition" if kind == 'position' else "setAnchorPoint"
                cpp_lines.append(f'    {var_name}->{func}(ccp({clean_x}, {clean_y}));')

        elif kind == 'pos_getter':
            text = matched_text.replace(" ", "")
            translated = re.sub(r'(\w+)\.position\.([xy])', r'\1->getPosition().\2', text)
            translated = re.sub(r'(\w+)\.position$', r'\1->getPosition()', translated)
            cpp_lines.append(f'    {translated}')

        elif kind == 'add_child':
            m = re.search(r'gds\s*\.\s*addChild\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', match.group('add_child'))
            cpp_lines.append(f"    {m.group(1)}->addChild({m.group(2)});")

        elif kind == 'speed':
    
            speed_pattern = r'gds\s*\.\s*speed\s*=\s*((\d+(\.\d*)?|\.\d+))[fF]?'
            m = re.search(speed_pattern, matched_text)
    
            if m:
                speed_value = m.group(1)
                cpp_lines.append(f'    CCDirector::sharedDirector()->setTimeScale({speed_value});')
            else:
                print(f"Warning: Failed to parse speed at '{matched_text}'")

        elif kind == 'member_offset':
            m = re.search(r'(\w+)\s*=\s*(?:<(?P<type>[\w.]*)>)?\s*(?P<obj>\w+)\s*\.\s*memberByOffset\s*\(\s*(?P<offset>[^)]+)\s*\)', matched_text)
            if m:
                target_var = m.group(1)
                gds_type = m.group('type')
                obj_name = m.group('obj')
                offset = m.group('offset').strip()

                macro_type_map = {
                    'gds.voidptr': 'void*',
                    'gds.int': 'int',
                    'gds.bool': 'bool',
                    'gds.float': 'float'
                }
                cpp_type = macro_type_map.get(gds_type, 'void*') if gds_type else 'void*'
                
                cpp_lines.append(f'    auto {target_var} = MEMBER_BY_OFFSET({cpp_type}, {obj_name}, {offset});')

        elif kind == 'return_cast':
            m = re.search(r'return\s+<(?P<type>[\w.]*)>\s*(?P<val>[^;}\s]+)', matched_text)
            if m:
                gds_type = m.group('type')
                cpp_type = gds_type.replace("gds.", "")
                val = m.group('val').strip()
                if cpp_type == "bool":
                    if val == "1": val = "true"
                    elif val == "0": val = "false"
                elif cpp_type == "string":
                    cpp_type = "std::string"
            
                cpp_lines.append(f'    return ({cpp_type}){val};')

        elif kind == 'return_stmt':
            full_match = match.group('return_stmt')
            value = full_match.split()[-1].strip()
            if value == "1" or value == "true":
                cpp_lines.append("    return true;")
            elif value == "0" or value == "false":
                cpp_lines.append("    return false;")
            else:
                cpp_lines.append(f"    return {value};")

        elif kind == 'menu_align':
            m = re.search(r'(\w+)\s*\.\s*alignment\s*=\s*"([^"]+)"', matched_text)
            if m:
                var_name = m.group(1)
                align_str = m.group(2)
                if ":" in align_str:
                    mode, padding = align_str.split(":")
                    if mode == "horizontal":
                        cpp_lines.append(f'    {var_name}->alignItemsHorizontally({padding});')
                    elif mode == "vertical":
                        cpp_lines.append(f'    {var_name}->alignItemsVertically({padding});')
                else:
                    if align_str == "horizontal":
                        cpp_lines.append(f'    {var_name}->alignItemsHorizontally();')


        elif kind == 'hook':
            hook_pattern = r'gds\s*\.\s*hook\s*\(\s*"([^"]+)"\s*,\s*\$(\w+)\s*,\s*(\w+)\s*\)'
            m = re.search(hook_pattern, matched_text)
            
            if m:
                address = m.group(1)
                func_name = m.group(2)
                cpp_lines.append(f'    HOOK("{address}", {func_name}_H, {func_name});')
            else:
                print(f"Error: Could not parse hook arguments in: {matched_text}")

        elif kind == 'patch':
            patch_pattern = r'gds\s*\.\s*patch\s*\(\s*([^,]+)\s*,\s*"([^"]+)"\s*\)'
            m = re.search(patch_pattern, matched_text)
    
            if m:
                
                address = m.group(1).strip()
                hex_data = m.group(2)
                if not any("pm.cpatch" in line for line in cpp_lines) and not patch_buffer:
                    cpp_lines.append("    PatchManager pm;")
                cpp_lines.append(f'    pm.cpatch({address}, "{hex_data}");')
                is_last_patch = True
                if i + 1 < len(matches):
                    if matches[i+1].lastgroup == 'patch':
                        is_last_patch = False
                if is_last_patch:
                    cpp_lines.append("    pm.Modify();")
        elif kind == 'assignment':
            m = re.search(r'(\w+)\s*=\s*([^;]+)', matched_text)
            if m:
                var_name = m.group(1)
                expression = m.group(2)
                expression = clean_coords(expression) 
                cpp_lines.append(f'    auto {var_name} = {expression};')

    return "\n".join(cpp_lines)

def format_params(params):
    type_map = {
        'gds.layer': 'CCLayer*',
        'gds.javavm': 'JavaVM*',
        'gds.void': 'void*',
        'gds.win_size': 'CCSize',
        'gds.int': 'int',
        'gds.string': 'std::string',
        'gds.bool': 'bool'
    }
    formatted = []
    for p in params:
        cpp_type = type_map.get(p['type'], p['type'].replace('gds.', ''))
        if p['name']:
            formatted.append(f"{cpp_type} {p['name']}")
        else:
            formatted.append(cpp_type)
    return ", ".join(formatted)


print("Generating .cpp file...")
code = generate_cpp(ast)
code = code.replace("gds.win_size", "CCDirector::sharedDirector()->getWinSize()")
code = code.replace("gds.getJavaVM()", "cocos2d::JniHelper::getJavaVM()")
from pathlib import Path
gds_file = Path(directory)
cpp_file = gds_file.with_suffix(".cpp")
output_dir = Path(cpp_file)
output_dir.parent.mkdir(parents=True, exist_ok=True)
cpp_file.write_text(code, encoding="utf-8")
print(f"File generated at: {cpp_file.absolute()}")