
with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('element={{', 'element={')
content = content.replace('}} />', '} />')
content = content.replace('current={{', 'current={')
content = content.replace('{{step ', '{step ')
content = content.replace('onSubmit={{', 'onSubmit={')
content = content.replace('error={{', 'error={')
content = content.replace('jobId={{', 'jobId={')
content = content.replace('apiBase={{', 'apiBase={')
content = content.replace('onComplete={{', 'onComplete={')
content = content.replace('onError={{', 'onError={')
content = content.replace('{{result.pathway?', '{result.pathway?')
content = content.replace('onClick={{', 'onClick={')
content = content.replace('result={{', 'result={')
content = content.replace('gapVector={{', 'gapVector={')
content = content.replace('pathway={{', 'pathway={')
content = content.replace('onSelectModule={{', 'onSelectModule={')
content = content.replace('size={{16}}', 'size={16}')
content = content.replace('{{<', '{<')
content = content.replace('}}>', '}>')
content = content.replace('{{(', '{(')
content = content.replace(')}}', ')}')

with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
