const input = document.querySelector('#platform-query');
const cards = [...document.querySelectorAll('[data-platform-search]')];

if (input && cards.length) {
  const count = document.querySelector('#platform-count');
  const empty = document.querySelector('#platform-empty');
  const update = () => {
    const terms = input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const card of cards) {
      const searchable = card.dataset.platformSearch.toLocaleLowerCase();
      card.hidden = !terms.every(term => searchable.includes(term));
      if (!card.hidden) visible += 1;
    }
    count.textContent = `${visible} of ${cards.length} tools shown`;
    empty.hidden = visible !== 0;
  };
  input.addEventListener('input', update);
  document.querySelector('#platform-clear').addEventListener('click', () => {
    input.value = '';
    update();
    input.focus();
  });
  // Jump links must reveal their destination even after an unrelated search.
  document.querySelectorAll('.quick a').forEach(link => link.addEventListener('click', () => {
    input.value = '';
    update();
  }));
  document.querySelector('#platform-search-controls').hidden = false;
  update();
}
