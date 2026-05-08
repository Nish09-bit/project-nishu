import os

folder = 'templates'

toggle_script = '''
<script>
// Theme load on page start
(function() {
    if(localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-mode');
    }
})();

function toggleTheme() {
    document.body.classList.toggle('light-mode');
    var btn = document.getElementById('themeBtn');
    if(document.body.classList.contains('light-mode')) {
        localStorage.setItem('theme', 'light');
        if(btn) btn.textContent = '☀️ Light';
    } else {
        localStorage.setItem('theme', 'dark');
        if(btn) btn.textContent = '🌙 Dark';
    }
}

// Set correct button text on load
window.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('themeBtn');
    if(btn) {
        if(document.body.classList.contains('light-mode')) {
            btn.textContent = '☀️ Light';
        } else {
            btn.textContent = '🌙 Dark';
        }
    }
});
</script>'''

for f in os.listdir(folder):
    path = os.path.join(folder, f)
    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()

    changed = False

    # Purana script hatao aur naya daalo
    if 'toggleTheme' in content:
        import re
        content = re.sub(
            r'<script>\s*// Theme.*?</script>',
            toggle_script,
            content,
            flags=re.DOTALL
        )
        changed = True

    if changed:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(content)
        print('✅ Fixed:', f)
    else:
        print('⏭️ Skipped:', f)

print('All done!')