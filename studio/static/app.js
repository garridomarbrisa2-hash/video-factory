const form = document.querySelector('#project-form');
const topic = document.querySelector('#topic');
const counter = document.querySelector('#counter');
const result = document.querySelector('#result');
const submit = document.querySelector('#submit');
const apiDialog = document.querySelector('#api-dialog');
const apiForm = document.querySelector('#api-form');
const apiStatus = document.querySelector('#api-status');
const apiMessage = document.querySelector('#api-message');
const saveApi = document.querySelector('#save-api');
const voiceApiDialog = document.querySelector('#voice-api-dialog');
const voiceApiForm = document.querySelector('#voice-api-form');
const voiceApiStatus = document.querySelector('#voice-api-status');
const voiceApiMessage = document.querySelector('#voice-api-message');
const saveVoiceApi = document.querySelector('#save-voice-api');
const voiceChoice = document.querySelector('#voice-choice');
const voiceSelect = document.querySelector('#voice-id');
const recent = document.querySelector('#recent');
const recentList = document.querySelector('#recent-list');
const pexelsApiDialog = document.querySelector('#pexels-api-dialog');
const pexelsApiForm = document.querySelector('#pexels-api-form');
const pexelsApiStatus = document.querySelector('#pexels-api-status');
const pexelsApiMessage = document.querySelector('#pexels-api-message');
const savePexelsApi = document.querySelector('#save-pexels-api');
const pixabayApiDialog = document.querySelector('#pixabay-api-dialog');
const pixabayApiForm = document.querySelector('#pixabay-api-form');
const pixabayApiStatus = document.querySelector('#pixabay-api-status');
const pixabayApiMessage = document.querySelector('#pixabay-api-message');
const savePixabayApi = document.querySelector('#save-pixabay-api');
const youtubeApiDialog = document.querySelector('#youtube-api-dialog');
const youtubeApiForm = document.querySelector('#youtube-api-form');
const youtubeApiStatus = document.querySelector('#youtube-api-status');
const youtubeApiMessage = document.querySelector('#youtube-api-message');
const saveYoutubeApi = document.querySelector('#save-youtube-api');
const youtubeImportDialog = document.querySelector('#youtube-import-dialog');
const youtubeImportForm = document.querySelector('#youtube-import-form');
const youtubeImportMessage = document.querySelector('#youtube-import-message');
const saveYoutubeImport = document.querySelector('#save-youtube-import');
const mediaReviewDialog = document.querySelector('#media-review-dialog');
const mediaSceneSelect = document.querySelector('#media-scene-select');
const mediaSceneContext = document.querySelector('#media-scene-context');
const mediaReviewResults = document.querySelector('#media-review-results');
const mediaReviewMessage = document.querySelector('#media-review-message');
let youtubeImportProject = '';
let youtubeImportEpisode = '';
let youtubeImportCandidates = [];
let mediaReviewScenes = [];

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
      Nenhuma API foi chamada e nenhum vídeo foi renderizado.
      <button class="generate-script" type="button" data-project="${escapeHtml(payload.project)}" data-episode="${payload.episode}">
        <span>Gerar roteiro com IA</span><span>→</span>
      </button>
      <div class="generation-status"></div>`;
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

result.addEventListener('click', async (event) => {
  const button = event.target.closest('.generate-script');
  if (!button) return;
  const accepted = window.confirm('Gerar o roteiro agora? Esta ação usa o saldo da API Anthropic. Se a duração sair incorreta, o sistema poderá fazer uma segunda chamada para ajustar o texto.');
  if (!accepted) return;

  const status = result.querySelector('.generation-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Gerando roteiro...';
  status.textContent = 'A IA está escrevendo. Isso pode levar alguns minutos; não feche esta página.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/script`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível gerar o roteiro.');
    button.remove();
    const quality = payload.duration_ok
      ? `Duração aprovada: aproximadamente ${escapeHtml(payload.estimated_minutes)} minutos.`
      : `Atenção: duração fora da meta (${escapeHtml(payload.target_min_words)}–${escapeHtml(payload.target_max_words)} palavras).`;
    status.innerHTML = `<strong>${payload.duration_ok ? 'Roteiro concluído ✓' : 'Roteiro precisa de revisão'}</strong>
      ${escapeHtml(payload.word_count)} palavras · modelo ${escapeHtml(payload.model)}.<br>
      ${quality}<br>
      Salvo em <code>${escapeHtml(payload.script_path)}</code>.
      <button class="review-script" type="button" data-project="${escapeHtml(button.dataset.project)}" data-episode="${escapeHtml(button.dataset.episode)}">
        <span>Enviar para o Revisor</span><span>→</span>
      </button>
      <div class="review-status"></div>`;
    status.classList.add(payload.duration_ok ? 'success' : 'error');
    await loadRecent();
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar gerar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

result.addEventListener('click', async (event) => {
  const button = event.target.closest('.review-script');
  if (!button) return;
  const accepted = window.confirm('Revisar o roteiro agora? Esta etapa usa o saldo da API Anthropic. É uma revisão editorial; afirmações que precisarem de fontes serão marcadas.');
  if (!accepted) return;

  const status = result.querySelector('.review-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Revisando...';
  status.textContent = 'O Revisor está analisando o roteiro. Isso pode levar alguns minutos.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/review`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível revisar o roteiro.');
    button.remove();
    const sourceMessage = payload.verification_count
      ? `${escapeHtml(payload.verification_count)} afirmação(ões) ainda precisam de fontes.`
      : 'Nenhuma afirmação adicional foi sinalizada.';
    status.innerHTML = `<strong>Revisão editorial concluída ✓</strong>
      ${escapeHtml(payload.word_count)} palavras · aproximadamente ${escapeHtml(payload.estimated_minutes)} minutos.<br>
      ${sourceMessage}<br>
      Roteiro: <code>${escapeHtml(payload.reviewed_path)}</code><br>
      Relatório: <code>${escapeHtml(payload.report_path)}</code>`;
    status.classList.add(payload.decision === 'approved' ? 'success' : 'error');
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar revisar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

function escapeHtml(value) {
  const node = document.createElement('div');
  node.textContent = value ?? '';
  return node.innerHTML;
}

document.querySelector('#open-api').addEventListener('click', () => apiDialog.showModal());
document.querySelector('#close-api').addEventListener('click', () => apiDialog.close());

async function refreshSettings() {
  try {
    const response = await fetch('/api/settings');
    const payload = await response.json();
    if (payload.anthropic.configured) {
      apiStatus.textContent = `Conectada · ${payload.anthropic.masked_key}`;
      apiStatus.classList.add('connected');
      document.querySelector('#open-api').textContent = 'Alterar';
    }
    if (payload.elevenlabs.configured) {
      voiceApiStatus.textContent = `Conectada · ${payload.elevenlabs.voice_name}`;
      voiceApiStatus.classList.add('connected');
      document.querySelector('#open-voice-api').textContent = 'Alterar';
    }
    if (payload.pexels.configured) {
      pexelsApiStatus.textContent = `Conectado · ${payload.pexels.masked_key}`;
      pexelsApiStatus.classList.add('connected');
      document.querySelector('#open-pexels-api').textContent = 'Alterar';
    }
    if (payload.pixabay.configured) {
      pixabayApiStatus.textContent = `Conectado · ${payload.pixabay.masked_key}`;
      pixabayApiStatus.classList.add('connected');
      document.querySelector('#open-pixabay-api').textContent = 'Alterar';
    }
    if (payload.youtube.configured) {
      youtubeApiStatus.textContent = `Conectado · ${payload.youtube.masked_key}`;
      youtubeApiStatus.classList.add('connected');
      document.querySelector('#open-youtube-api').textContent = 'Alterar';
    }
  } catch (_) {
    apiStatus.textContent = 'Não foi possível verificar';
  }
}

apiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  apiMessage.textContent = '';
  apiMessage.classList.remove('success');
  saveApi.disabled = true;
  saveApi.firstElementChild.textContent = 'Testando...';
  try {
    const response = await fetch('/api/settings/anthropic', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: document.querySelector('#api-key').value}),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível conectar.');
    document.querySelector('#api-key').value = '';
    apiMessage.textContent = payload.message;
    apiMessage.classList.add('success');
    await refreshSettings();
    setTimeout(() => apiDialog.close(), 1200);
  } catch (error) {
    apiMessage.textContent = error.message;
  } finally {
    saveApi.disabled = false;
    saveApi.firstElementChild.textContent = 'Testar e salvar';
  }
});

refreshSettings();

async function loadRecent() {
  try {
    const response = await fetch('/api/projects/recent');
    const payload = await response.json();
    if (!payload.episodes?.length) {
      recent.hidden = true;
      return;
    }
    recentList.innerHTML = payload.episodes.map((episode) => {
      let action;
      if (episode.media_candidates) {
        action = `<div class="episode-actions"><span class="stage-complete">Mídia localizada ✓</span>
          <button class="open-media-review" type="button" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>Revisar Pexels e Pixabay</span><span>→</span></button>
          <button class="search-media secondary-action" type="button" data-refresh="true" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>Refazer busca inteligente</span><span>↻</span></button>
          <button class="open-youtube-import youtube-exception" type="button" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>YouTube (opcional)</span><span>→</span></button></div>`;
      } else if (episode.direction) {
        action = `<button class="search-media" type="button" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>Buscar elementos visuais</span><span>→</span></button>`;
      } else if (episode.narration) {
        action = `<div class="episode-actions"><audio controls preload="none" src="/api/projects/${escapeHtml(episode.project)}/episodes/${escapeHtml(episode.episode)}/narration/audio"></audio>
          <button class="generate-director" type="button" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>Criar direção de cenas</span><span>→</span></button></div>`;
      } else {
        action = `<button class="generate-narration" type="button" data-project="${escapeHtml(episode.project)}" data-episode="${escapeHtml(episode.episode)}"><span>Gerar narração</span><span>→</span></button>`;
      }
      return `<article class="episode-card">
        <div><strong>${escapeHtml(episode.topic)}</strong><small>Episódio ${escapeHtml(episode.episode)}${episode.reviewed ? ' · revisado' : ''}</small></div>
        ${action}
        <div class="episode-action-status"></div>
      </article>`;
    }).join('');
    recent.hidden = false;
  } catch (_) {
    recent.hidden = true;
  }
}

recentList.addEventListener('click', async (event) => {
  const button = event.target.closest('.generate-narration');
  if (!button) return;
  const accepted = window.confirm('Gerar a narração completa agora? Esta ação usa os créditos de caracteres da ElevenLabs.');
  if (!accepted) return;
  const card = button.closest('.episode-card');
  const status = card.querySelector('.episode-action-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Gerando voz...';
  status.textContent = 'A ElevenLabs está narrando o roteiro em partes. Isso pode levar alguns minutos; não feche esta página.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/narration`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível gerar a narração.');
    button.remove();
    const gate = payload.status === 'approved'
      ? 'Duração aprovada para seguir ao Diretor.'
      : 'A duração ficou fora de 8–20 minutos; o roteiro precisa ser ajustado antes do Diretor.';
    status.innerHTML = `<strong>Narração concluída ✓</strong>
      ${escapeHtml(payload.total_minutes)} minutos · ${escapeHtml(payload.beat_count)} trechos.<br>
      ${gate}<br>
      Áudio salvo em <code>${escapeHtml(payload.audio_path)}</code>.<br>
      <audio controls preload="metadata" src="/api/projects/${escapeHtml(button.dataset.project)}/episodes/${escapeHtml(button.dataset.episode)}/narration/audio"></audio>`;
    status.classList.add(payload.status === 'approved' ? 'success' : 'error');
    if (payload.status === 'approved') await loadRecent();
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

recentList.addEventListener('click', async (event) => {
  const button = event.target.closest('.generate-director');
  if (!button) return;
  const accepted = window.confirm('Criar a direção visual agora? Esta ação usa o saldo da API Anthropic e poderá fazer várias chamadas pequenas para planejar todas as cenas com segurança.');
  if (!accepted) return;
  const card = button.closest('.episode-card');
  const status = card.querySelector('.episode-action-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Dirigindo cenas...';
  status.textContent = 'O Diretor está sincronizando imagens e cenas com a narração. Isso pode levar alguns minutos.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/director`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível criar a direção.');
    button.remove();
    status.innerHTML = `<strong>Direção concluída ✓</strong>
      ${escapeHtml(payload.scene_count)} cenas sincronizadas.<br>
      Plano salvo em <code>${escapeHtml(payload.direction_path)}</code>.<br>
      Próxima etapa: preparar os elementos visuais.`;
    status.classList.add('success');
    await loadRecent();
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

recentList.addEventListener('click', async (event) => {
  const button = event.target.closest('.search-media');
  if (!button) return;
  const accepted = window.confirm('Fazer uma busca contextual? Pexels e Pixabay continuam como base. O YouTube também pode localizar até 10 vídeos relacionados ao tema central, para trechos opcionais de até 5 segundos. Nenhum vídeo será baixado.');
  if (!accepted) return;
  const card = button.closest('.episode-card');
  const status = card.querySelector('.episode-action-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Pesquisando...';
  status.textContent = 'O Agente de Mídia está pesquisando primeiro no Pexels e Pixabay. Pode levar alguns minutos; não feche esta página.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/media-search`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({refresh: button.dataset.refresh === 'true'}),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível buscar os elementos visuais.');
    if (!button.dataset.refresh) button.remove();
    const providers = Object.entries(payload.provider_counts || {})
      .map(([name, count]) => `${name}: ${count.candidates} candidato(s)`)
      .join(' · ');
    const pending = payload.pending_scene_count
      ? `<br>${escapeHtml(payload.pending_scene_count)} cena(s) ficaram pendentes para mídia manual, gerada ou provedor ainda não configurado.`
      : '';
    status.innerHTML = `<strong>Busca contextual concluída ✓</strong>
      ${escapeHtml(payload.scene_count)} cenas · ${escapeHtml(payload.candidate_count)} candidatos.<br>
      ${escapeHtml(providers)}${pending}<br>
      Salvo em <code>${escapeHtml(payload.path)}</code>.<br>
      Nenhum vídeo foi baixado.`;
    status.classList.add('success');
    await loadRecent();
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

loadRecent();

function renderMediaScene() {
  const sceneIndex = Number(mediaSceneSelect.value || 0);
  const scene = mediaReviewScenes[sceneIndex];
  if (!scene) {
    mediaSceneContext.innerHTML = '';
    mediaReviewResults.innerHTML = '<div class="empty-media-state">Nenhuma cena foi encontrada.</div>';
    return;
  }

  const stockCandidates = (scene.candidates || []).filter((candidate) =>
    candidate.provider === 'pexels' || candidate.provider === 'pixabay'
  );
  mediaSceneContext.innerHTML = `<strong>Cena ${escapeHtml(scene.scene_id)}</strong>
    <span>${escapeHtml(scene.context || scene.topic || scene.query || '')}</span>
    <small>Busca: ${escapeHtml(scene.query || 'sem termo registrado')}</small>`;

  mediaReviewResults.innerHTML = stockCandidates.length
    ? stockCandidates.map((candidate) => {
        const provider = candidate.provider === 'pixabay' ? 'Pixabay' : 'Pexels';
        const sourceUrl = candidate.pixabay_url || candidate.pexels_url || '#';
        const preview = candidate.video_url
          ? `<video controls muted playsinline preload="metadata" ${candidate.preview_image ? `poster="${escapeHtml(candidate.preview_image)}"` : ''} src="${escapeHtml(candidate.video_url)}"></video>`
          : candidate.preview_image
            ? `<img loading="lazy" src="${escapeHtml(candidate.preview_image)}" alt="Prévia da cena ${escapeHtml(scene.scene_id)}">`
            : '<div class="media-no-preview">Prévia indisponível</div>';
        return `<article class="media-candidate-card">
          ${preview}
          <div class="media-candidate-info">
            <span class="provider-badge ${escapeHtml(candidate.provider)}">${provider}</span>
            <strong>${escapeHtml(candidate.matched_query || scene.query || 'Resultado visual')}</strong>
            <small>${escapeHtml(candidate.creator ? `por ${candidate.creator}` : 'Mídia do banco')}</small>
            <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Abrir página original ↗</a>
          </div>
        </article>`;
      }).join('')
    : `<div class="empty-media-state"><strong>Sem resultado de banco nesta cena.</strong><span>Refaça a busca ou prepare uma mídia manual. O YouTube permanece apenas como alternativa.</span></div>`;

  document.querySelector('#previous-media-scene').disabled = sceneIndex <= 0;
  document.querySelector('#next-media-scene').disabled = sceneIndex >= mediaReviewScenes.length - 1;
}

recentList.addEventListener('click', async (event) => {
  const button = event.target.closest('.open-media-review');
  if (!button) return;
  mediaReviewScenes = [];
  mediaSceneSelect.innerHTML = '<option>Carregando cenas...</option>';
  mediaReviewResults.innerHTML = '<div class="empty-media-state">Carregando opções do Pexels e Pixabay...</div>';
  mediaReviewMessage.textContent = '';
  mediaReviewDialog.showModal();
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/media-candidates`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível carregar as opções visuais.');
    mediaReviewScenes = payload.scenes || [];
    mediaSceneSelect.innerHTML = mediaReviewScenes.map((scene, index) => {
      const stockCount = (scene.candidates || []).filter((candidate) => candidate.provider === 'pexels' || candidate.provider === 'pixabay').length;
      return `<option value="${index}">Cena ${escapeHtml(scene.scene_id)} · ${stockCount} opção(ões)</option>`;
    }).join('');
    renderMediaScene();
  } catch (error) {
    mediaReviewScenes = [];
    mediaReviewResults.innerHTML = '';
    mediaReviewMessage.textContent = error.message;
  }
});

document.querySelector('#close-media-review').addEventListener('click', () => mediaReviewDialog.close());
mediaSceneSelect.addEventListener('change', renderMediaScene);
document.querySelector('#previous-media-scene').addEventListener('click', () => {
  mediaSceneSelect.value = String(Math.max(0, Number(mediaSceneSelect.value) - 1));
  renderMediaScene();
});
document.querySelector('#next-media-scene').addEventListener('click', () => {
  mediaSceneSelect.value = String(Math.min(mediaReviewScenes.length - 1, Number(mediaSceneSelect.value) + 1));
  renderMediaScene();
});

recentList.addEventListener('click', async (event) => {
  const button = event.target.closest('.open-youtube-import');
  if (!button) return;
  youtubeImportProject = button.dataset.project;
  youtubeImportEpisode = button.dataset.episode;
  youtubeImportMessage.textContent = '';
  youtubeImportMessage.classList.remove('success');
  youtubeImportDialog.showModal();
  const select = document.querySelector('#youtube-import-candidate');
  select.innerHTML = '<option value="">Carregando candidatos...</option>';
  try {
    const response = await fetch(`/api/projects/${youtubeImportProject}/episodes/${youtubeImportEpisode}/media-candidates`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível carregar os candidatos.');
    const discoveredCandidates = (payload.scenes || []).flatMap((scene) =>
      (scene.candidates || [])
        .filter((candidate) => candidate.youtube_url)
        .map((candidate) => ({...candidate, scene_id: scene.scene_id}))
    );
    youtubeImportCandidates = [...new Map(discoveredCandidates.map((candidate) => [candidate.youtube_url, candidate])).values()].slice(0, 10);
    select.innerHTML = youtubeImportCandidates.length
      ? youtubeImportCandidates.map((candidate, index) => `<option value="${index}">Cena ${escapeHtml(candidate.scene_id)} · ${escapeHtml(candidate.title || candidate.channel || 'Vídeo do YouTube')}</option>`).join('')
      : '<option value="">Nenhum candidato do YouTube foi encontrado</option>';
    saveYoutubeImport.disabled = !youtubeImportCandidates.length;
  } catch (error) {
    youtubeImportCandidates = [];
    select.innerHTML = '<option value="">Não foi possível carregar</option>';
    saveYoutubeImport.disabled = true;
    youtubeImportMessage.textContent = error.message;
  }
});

document.querySelector('#close-youtube-import').addEventListener('click', () => youtubeImportDialog.close());

youtubeImportForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  youtubeImportMessage.textContent = '';
  youtubeImportMessage.classList.remove('success');
  saveYoutubeImport.disabled = true;
  saveYoutubeImport.firstElementChild.textContent = 'Importando...';
  try {
    const candidate = youtubeImportCandidates[Number(document.querySelector('#youtube-import-candidate').value)];
    if (!candidate) throw new Error('Escolha um candidato do YouTube.');
    const startSeconds = Number(document.querySelector('#youtube-import-start').value);
    const endSeconds = Number(document.querySelector('#youtube-import-end').value);
    if (endSeconds <= startSeconds || endSeconds - startSeconds > 5) {
      throw new Error('Escolha um trecho de no máximo 5 segundos.');
    }
    const response = await fetch(`/api/projects/${youtubeImportProject}/episodes/${youtubeImportEpisode}/youtube-import`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        scene_id: Number(candidate.scene_id),
        youtube_url: candidate.youtube_url,
        start_seconds: startSeconds,
        end_seconds: endSeconds,
        rights_confirmed: document.querySelector('#youtube-import-rights').checked,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível importar o trecho.');
    youtubeImportMessage.innerHTML = `Trecho importado ✓<br>Salvo em <code>${escapeHtml(payload.media_path)}</code>.`;
    youtubeImportMessage.classList.add('success');
  } catch (error) {
    youtubeImportMessage.textContent = error.message;
  } finally {
    saveYoutubeImport.disabled = false;
    saveYoutubeImport.firstElementChild.textContent = 'Importar e recortar';
  }
});

document.querySelector('#open-voice-api').addEventListener('click', () => voiceApiDialog.showModal());
document.querySelector('#close-voice-api').addEventListener('click', () => voiceApiDialog.close());

voiceApiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  voiceApiMessage.textContent = '';
  voiceApiMessage.classList.remove('success');
  saveVoiceApi.disabled = true;
  saveVoiceApi.firstElementChild.textContent = voiceChoice.hidden ? 'Testando...' : 'Salvando...';
  try {
    const key = document.querySelector('#voice-api-key').value;
    const body = {api_key: key};
    if (!voiceChoice.hidden) body.voice_id = voiceSelect.value;
    const response = await fetch('/api/settings/elevenlabs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível conectar.');
    if (!payload.configured) {
      voiceSelect.innerHTML = payload.voices.map((voice) =>
        `<option value="${escapeHtml(voice.voice_id)}">${escapeHtml(voice.name)}${voice.category ? ` · ${escapeHtml(voice.category)}` : ''}</option>`
      ).join('');
      voiceChoice.hidden = false;
      voiceApiMessage.textContent = payload.message;
      voiceApiMessage.classList.add('success');
      saveVoiceApi.firstElementChild.textContent = 'Salvar voz escolhida';
      return;
    }
    document.querySelector('#voice-api-key').value = '';
    voiceChoice.hidden = true;
    voiceApiMessage.textContent = payload.message;
    voiceApiMessage.classList.add('success');
    await refreshSettings();
    setTimeout(() => voiceApiDialog.close(), 1200);
  } catch (error) {
    voiceApiMessage.textContent = error.message;
  } finally {
    saveVoiceApi.disabled = false;
    if (voiceChoice.hidden) saveVoiceApi.firstElementChild.textContent = 'Testar e escolher voz';
  }
});

document.querySelector('#open-pexels-api').addEventListener('click', () => pexelsApiDialog.showModal());
document.querySelector('#close-pexels-api').addEventListener('click', () => pexelsApiDialog.close());

pexelsApiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  pexelsApiMessage.textContent = '';
  pexelsApiMessage.classList.remove('success');
  savePexelsApi.disabled = true;
  savePexelsApi.firstElementChild.textContent = 'Testando...';
  try {
    const response = await fetch('/api/settings/pexels', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: document.querySelector('#pexels-api-key').value}),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível conectar ao Pexels.');
    document.querySelector('#pexels-api-key').value = '';
    pexelsApiMessage.textContent = payload.message;
    pexelsApiMessage.classList.add('success');
    await refreshSettings();
    setTimeout(() => pexelsApiDialog.close(), 1200);
  } catch (error) {
    pexelsApiMessage.textContent = error.message;
  } finally {
    savePexelsApi.disabled = false;
    savePexelsApi.firstElementChild.textContent = 'Testar e salvar';
  }
});

function bindMediaProvider({name, dialog, form, message, saveButton}) {
  document.querySelector(`#open-${name}-api`).addEventListener('click', () => dialog.showModal());
  document.querySelector(`#close-${name}-api`).addEventListener('click', () => dialog.close());
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    message.textContent = '';
    message.classList.remove('success');
    saveButton.disabled = true;
    saveButton.firstElementChild.textContent = 'Testando...';
    try {
      const response = await fetch(`/api/settings/${name}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({api_key: document.querySelector(`#${name}-api-key`).value}),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `Não foi possível conectar ao ${name}.`);
      document.querySelector(`#${name}-api-key`).value = '';
      message.textContent = payload.message;
      message.classList.add('success');
      await refreshSettings();
      setTimeout(() => dialog.close(), 1200);
    } catch (error) {
      message.textContent = error.message;
    } finally {
      saveButton.disabled = false;
      saveButton.firstElementChild.textContent = 'Testar e salvar';
    }
  });
}

bindMediaProvider({name: 'pixabay', dialog: pixabayApiDialog, form: pixabayApiForm, message: pixabayApiMessage, saveButton: savePixabayApi});
bindMediaProvider({name: 'youtube', dialog: youtubeApiDialog, form: youtubeApiForm, message: youtubeApiMessage, saveButton: saveYoutubeApi});
