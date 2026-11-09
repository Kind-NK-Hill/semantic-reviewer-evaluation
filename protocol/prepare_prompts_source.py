import difflib
import re
import shutil
import textwrap
from common import ROOT,save,load,note,sha

def main():
    doc=(ROOT/'reviewer_calibration_TASK.md').read_text(encoding='utf-8')
    blocks=[textwrap.dedent(m.group(1)).strip('\n') for m in re.finditer(r'```text\n(.*?)\n\s*```',doc,re.S)]
    def take(prefix):
        found=[s for s in blocks if s.startswith(prefix)];assert len(found)==1,(prefix,len(found));return found[0]
    parts={'common':take('You will be given a natural-language mathematics problem'),
           'output':take('Return JSON with two fields: "verdict"'),
           'input':take('<problem>'),
           'R1':take('Apply these criteria:'),
           'R0a':take('Below are a mathematics problem'),
           'R0b':take('Your input consists of a mathematics problem'),
           'label':take('You will be given the reason a human annotator wrote')}
    paper=(ROOT/'reviews/2026-11-05_plan_audit/sources/2510.24592v3.txt').read_text(encoding='utf-8')
    start=paper.index('Your role is a Lean4 expert, please help me check consistency')
    stop=paper.index('\nD.3\n',start)
    original=paper[start:stop]
    core=original.split('Intput Format')[0].strip()
    changes=[]
    def replace(old,new,reason):
        nonlocal core
        assert old in core,old
        core=core.replace(old,new)
        changes.append({'old':old,'new':new,'reason':reason})
    replace('- If any result is Incorrect of consistency, briefly list all inconsistencies and reasons leading to the Incorrect determination in comments',
            parts['output'],'输出 comments 的要求替换为共同输出要求。')
    replace('- Result must be strictly ”Correct” or ”Incorrect”',parts['output'],'二分类输出格式替换为共同三分类 JSON 输出要求。')
    replace('- Use ”Correct” ONLY when 100% mathematical equivalence is confirmed','- Use ”faithful” ONLY when 100% mathematical equivalence is confirmed','按任务单将正确映射为 faithful，保留确认条件。')
    replace('If correct: clearly confirm why all elements match.\nIf incorrect: list all mismatches and explain how each one affects correctness.',
            parts['output'],'步骤 5 的输出解释要求替换为共同一句理由要求；步骤标题保留。')
    changes.append({'old':original[original.index('Intput Format'):],'new':parts['output']+'\n\n'+parts['input'],
                    'reason':'替换原输入占位、前轮历史输入和 XML 输出块；本实验没有前轮历史。'})
    parts['R1g']=core
    for heading in ['1. Math Assertion Analysis','2. Lean Statement Analysis','3. Comparative Verification','4. Final Judgement','5. Accuracy Confirmation']:
        assert heading in core
    # The entire substantive comparison block is preserved verbatim.
    comp=original.split('3. Comparative Verification\n')[1].split('4. Final Judgement')[0]
    assert comp in core
    save(ROOT/'prompts/parts.json',parts)
    for name in ['R0','R1','R1g','R0a','R0b']:
        head=parts[name] if name in ('R0a','R0b') else parts['common']
        criteria=parts[name] if name in ('R1','R1g') else None
        pieces=[head]+([criteria] if criteria else [])+[parts['output'],parts['input']]
        text='\n\n'.join(pieces)
        (ROOT/'prompts'/f'{name}.txt').write_text(text,encoding='utf-8')
        assert all(p in text for p in pieces)
    (ROOT/'labels/error_type_prompt.txt').write_text(parts['label'],encoding='utf-8')
    save(ROOT/'prompts/verdict.schema.json',{'type':'object','properties':{'verdict':{'type':'string','enum':['faithful','unfaithful','uncertain']},'reason':{'type':'string'}},'required':['verdict','reason'],'additionalProperties':False})
    save(ROOT/'labels/category.schema.json',{'type':'object','properties':{'category':{'type':'string','enum':[f'C{i}' for i in range(7)]},'quote':{'type':'string'}},'required':['category','quote'],'additionalProperties':False})
    (ROOT/'prompts/R1g_original.txt').write_text(original,encoding='utf-8')
    save(ROOT/'prompts/R1g_changes.json',changes)
    source='# R1g 来源与逐项改编\n\n来源：ReForm arXiv 2510.24592v3，附录 D.2；原论文 PDF 和 HTML 已保存在 data/raw/sources，哈希见 data/raw/manifest.json。\n\n## 原文\n\n```text\n'+original+'\n```\n\n## 改编记录\n'
    for i,c in enumerate(changes,1):
        source+=f'\n### {i}. {c["reason"]}\n\n原文：\n```text\n{c["old"]}\n```\n\n替换：\n```text\n{c["new"]}\n```\n'
        note(f'R1g 改编 {i}：{c["reason"]} 逐字差异见 prompts/R1g_changes.json。')
    (ROOT/'prompts/R1g_source.md').write_text(source,encoding='utf-8')
    save(ROOT/'prompts/manifest.json',{p.name:{'sha256':sha(p),'words':len(p.read_text(encoding='utf-8').split())} for p in (ROOT/'prompts').glob('*.txt')})
    print('Prompts assembled and source comparisons verified.')

def ablation(k):
    parts=load(ROOT/'prompts/parts.json')
    lines=parts['R1'].splitlines();kept=[lines[0]]
    for number,line in enumerate(lines[1:],1):
        if number==k:continue
        if k==3:line=line.replace(' This rule takes precedence over criterion 3.','')
        line=re.sub(r'^\d+\.',str(len(kept))+'.',line);kept.append(line)
    text='\n\n'.join([parts['common'],'\n'.join(kept),parts['output'],parts['input']])
    (ROOT/'prompts/R1-k.txt').write_text(text,encoding='utf-8')
    manifest=load(ROOT/'prompts/manifest.json')
    manifest['R1-k.txt']={'sha256':sha(ROOT/'prompts/R1-k.txt'),'words':len(text.split())}
    save(ROOT/'prompts/manifest.json',manifest)

if __name__=='__main__':main()
