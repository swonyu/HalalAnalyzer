"""Read-only OpenStep project parser; no native commands or mutation."""
import json,re
TOKEN=re.compile(r'\s+|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,]+')
def parse(text):
 tokens=[]; end=0
 for match in TOKEN.finditer(text):
  assert match.start()==end,('unparsed bytes',end)
  end=match.end(); token=match.group()
  if token.isspace() or token.startswith('//') or token.startswith('/*'):continue
  tokens.append(token)
 assert end==len(text),'unparsed trailing bytes'
 cursor=0
 def take(expected=None):
  nonlocal cursor
  assert cursor<len(tokens),'unexpected EOF'
  value=tokens[cursor]; cursor+=1
  assert expected is None or value==expected,(expected,value)
  return value
 def scalar(token):return json.loads(token) if token.startswith('"') else token
 def value():
  token=take()
  if token=='{':
   result={}
   while tokens[cursor]!='}':
    key=scalar(take()); assert key not in result,('duplicate key',key)
    take('='); result[key]=value(); take(';')
   take('}'); return result
  if token=='(':
   result=[]
   while tokens[cursor]!=')':
    result.append(value())
    if tokens[cursor]==',':take(',')
    else:assert tokens[cursor]==')','missing list comma'
   take(')'); return result
  assert token not in '=;,})',('unexpected token',token)
  return scalar(token)
 result=value(); assert cursor==len(tokens),'trailing tokens'; return result

