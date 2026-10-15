const list = document.querySelector('#directory');
const status = document.querySelector('#directory-status');
const filter = document.querySelector('#segment');
const textElement = (tag, value) => {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
};
try {
  const response = await fetch('agent-ecosystem.json');
  if (!response.ok) throw new Error('directory unavailable');
  const catalog = await response.json();
  function render() {
    const targets = catalog.targets.filter(target => filter.value === 'all' || target.segment === filter.value);
    list.replaceChildren();
    for (const target of targets) {
      const card = document.createElement('article');
      card.append(textElement('p', `${target.segment} · ${target.kind}`), textElement('h3', target.name), textElement('p', target.workflow));
      const link = textElement('a', 'Read the official source');
      const url = new URL(target.source_url);
      if (url.protocol !== 'https:') throw new Error('invalid source');
      link.href = url.href;
      card.append(link, textElement('p', 'Data connection: not enrolled'));
      list.append(card);
    }
    status.textContent = `${targets.length} integration opportunities. Global agent coverage is unknown.`;
  }
  filter.addEventListener('change', render);
  render();
} catch {
  status.textContent = 'The directory could not load. Use the JSON download or try again.';
}
