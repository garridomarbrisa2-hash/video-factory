const form = document.querySelector('#project-form');
const topic = document.querySelector('#topic');
const counter = document.querySelector('#counter');
const result = document.querySelector('#result');
const submit = document.querySelector('#submit');

topic.addEventListener('input', () => {
  counter.textContent = `${topic.value.length}/500`;
});

document.querySelectorAll('.style-card').forEach((card) => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.style-card').forEach((item) => item.classList.remove('selected'));
    card.classList.add('selected');
  });
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  result.hidden = true;
  result.classList.remove('error');
  submit.disabled = true;
  submit.firstElementChild.textContent = 'Criando...';

  const data = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch('/api/projects', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível criar o projeto.');

    result.innerHTML = `<strong>Projeto criado com sucesso ✓</strong>
      Estilo escolhido: ${escapeHtml(payload.style_label)}.<br>
      Brief salvo em <code>${escapeHtml(payload.brief_path)}</code>.<br>
      Nenhuma API foi chamada e nenhum vídeo foi renderizado.`;
    result.hidden = false;
    result.scrollIntoView({behavior: 'smooth', block: 'center'});
  } catch (error) {
    result.textContent = error.message;
    result.classList.add('error');
    result.hidden = false;
  } finally {
    submit.disabled = false;
    submit.firstElementChild.textContent = 'Criar projeto';
  }
});

function escapeHtml(value) {
  const node = document.createElement('div');
  node.textContent = value ?? '';
  return node.innerHTML;
}

