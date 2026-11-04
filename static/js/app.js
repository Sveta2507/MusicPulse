/* Клієнтська логіка пошуку, карток, діалогу та оновлення Wikidata. */
document.addEventListener("DOMContentLoaded", () => {
  const grid = document.querySelector("#artistGrid");
  if (!grid) return;

  const count = document.querySelector("#resultCount");
  const dialog = document.querySelector("#artistDialog");
  const content = document.querySelector("#dialogContent");
  const toast = document.querySelector("#toast");
  const controls = ["search", "genre", "type", "sort"]
    .map((id) => document.querySelector(`#${id}`));

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);

  const initials = (name) => name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2);

  function artistImage(item, large = false) {
    if (item.image_url) {
      return `<img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.name_uk)}" loading="lazy" referrerpolicy="no-referrer">`;
    }
    return `<div class="image-fallback ${large ? "large" : ""}">${escapeHtml(initials(item.name_uk))}</div>`;
  }

  function card(item, index) {
    const genres = item.genres.slice(0, 3).map((genre) => `<span>${escapeHtml(genre.name)}</span>`).join("");
    return `<article class="artist-card" data-qid="${item.qid}" style="--delay:${index * 35}ms" tabindex="0">
      <div class="artist-image">${artistImage(item)}<span class="year">${item.start_year || "—"}</span></div>
      <div class="artist-body"><div class="type-line">${item.artist_type === "person" ? "СОЛЬНИЙ АРТИСТ" : "МУЗИЧНИЙ ГУРТ"}</div>
      <h3>${escapeHtml(item.name_uk)}</h3><div class="genre-tags">${genres}</div>
      <button type="button" aria-label="Відкрити ${escapeHtml(item.name_uk)}">Детальніше <span>↗</span></button></div>
    </article>`;
  }

  async function loadArtists() {
    const params = new URLSearchParams({
      search: controls[0].value, genre: controls[1].value,
      type: controls[2].value, sort: controls[3].value
    });
    grid.classList.add("loading");
    try {
      const response = await fetch(`/api/artists?${params}`);
      const data = await response.json();
      grid.innerHTML = data.items.length
        ? data.items.map(card).join("")
        : `<div class="empty-state"><b>Нічого не знайдено</b><span>Спробуйте змінити фільтри.</span></div>`;
      count.textContent = `${data.count} ${data.count === 1 ? "результат" : "результатів"}`;
      bindCards();
    } catch (_error) {
      grid.innerHTML = `<div class="empty-state"><b>Дані тимчасово недоступні</b><span>Перевірте запуск сервера.</span></div>`;
    } finally {
      grid.classList.remove("loading");
    }
  }

  async function openArtist(qid) {
    const response = await fetch(`/api/artists/${qid}`);
    if (!response.ok) return;
    const item = await response.json();
    const links = [
      item.spotify_url && `<a href="${escapeHtml(item.spotify_url)}" target="_blank" rel="noreferrer">Spotify ↗</a>`,
      item.youtube_url && `<a href="${escapeHtml(item.youtube_url)}" target="_blank" rel="noreferrer">YouTube ↗</a>`,
      `<a href="${escapeHtml(item.wikidata_url)}" target="_blank" rel="noreferrer">Wikidata ↗</a>`
    ].filter(Boolean).join("");
    content.innerHTML = `<div class="dialog-image">${artistImage(item, true)}</div><div class="dialog-copy">
      <div class="eyebrow"><span></span>${item.artist_type === "person" ? "СОЛЬНИЙ АРТИСТ" : "МУЗИЧНИЙ ГУРТ"} · ${item.qid}</div>
      <h2>${escapeHtml(item.name_uk)}</h2><p class="alt-name">${escapeHtml(item.name_en)}</p>
      <p>${escapeHtml(item.description)}</p><div class="genre-tags large">${item.genres.map((g) => `<span>${escapeHtml(g.name)}</span>`).join("")}</div>
      <div class="detail-meta"><div><span>Початок / рік народження</span><b>${item.start_year || "немає даних"}</b></div><div><span>Джерело</span><b>Wikidata · CC0</b></div></div>
      <div class="dialog-links">${links}</div></div>`;
    dialog.showModal();
    history.replaceState(null, "", `?artist=${qid}`);
  }

  function bindCards() {
    grid.querySelectorAll(".artist-card").forEach((element) => {
      const open = () => openArtist(element.dataset.qid);
      element.addEventListener("click", open);
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") open();
      });
    });
  }

  let timer;
  controls.forEach((control) => control.addEventListener(control.id === "search" ? "input" : "change", () => {
    clearTimeout(timer); timer = setTimeout(loadArtists, 180);
  }));

  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => history.replaceState(null, "", location.pathname));

  document.querySelector("#refreshButton")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true; button.textContent = "Оновлення…";
    try {
      const response = await fetch("/api/refresh", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      toast.textContent = `Оновлено ${data.artists} виконавців · ${data.triples} RDF-трійок`;
      toast.classList.add("visible"); await loadArtists();
    } catch (error) {
      toast.textContent = `Wikidata недоступна. Локальні дані збережено.`;
      toast.classList.add("visible");
    } finally {
      button.disabled = false; button.textContent = "Оновити дані";
      setTimeout(() => toast.classList.remove("visible"), 4000);
    }
  });

  fetch("/api/stats").then((response) => response.json()).then((data) => {
    const max = Math.max(...data.top_genres.map((item) => item.count), 1);
    document.querySelector("#genreChart").innerHTML = data.top_genres.map((item) =>
      `<div class="bar-row"><span>${escapeHtml(item.name)}</span><div><i style="width:${item.count / max * 100}%"></i></div><b>${item.count}</b></div>`
    ).join("");
  });

  loadArtists().then(() => {
    const qid = new URLSearchParams(location.search).get("artist");
    if (/^Q\d+$/.test(qid || "")) openArtist(qid);
  });
});

