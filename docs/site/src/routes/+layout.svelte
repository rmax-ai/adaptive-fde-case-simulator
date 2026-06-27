<script>
  import { base } from "$app/paths";
  import { browser } from "$app/environment";
  import { page } from "$app/stores";

  let { children } = $props();

  let mobileOpen = false;


  const nav = [
    { href: "/", label: "Home" },
    { href: "/architecture/", label: "Architecture" },
    { href: "/phases/", label: "Phases" },
    { href: "/demo/", label: "Demo" },
  ];

  function isActive(href) {
    const path = browser ? $page.url.pathname : "";
    if (href === "/") return path === base + "/" || path === base;
    return path.startsWith(base + href);
  }
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
</svelte:head>

<header>
  <div class="header-inner">
    <a href={base + "/"} class="logo">
      <span class="logo-icon">&#9670;</span>
      <span>AFCS</span>
    </a>
    <button class="mobile-toggle" onclick={() => mobileOpen = !mobileOpen}>
      {mobileOpen ? "✕" : "☰"}
    </button>
    <nav class:open={mobileOpen}>
      {#each nav as { href, label }}
        <a href={base + href} class:active={isActive(href)}>{label}</a>
      {/each}
      <a href="https://github.com/rmax-ai/adaptive-fde-case-simulator" class="gh-link" target="_blank" rel="noopener">
        GitHub ↗
      </a>
    </nav>
  </div>
</header>

<main>
  {@render children()}
</main>

<footer>
  <div class="footer-inner">
    <p>AFCS — Adaptive Forward Deployed Engineer Case Simulator</p>
    <p>MIT License · <a href="https://github.com/rmax-ai/adaptive-fde-case-simulator">rmax-ai/adaptive-fde-case-simulator</a></p>
  </div>
</footer>

<style>
  :global(*) { margin: 0; padding: 0; box-sizing: border-box; }
  :global(body) {
    font-family: "Inter", system-ui, sans-serif;
    background: #020617;
    color: #e2e8f0;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  :global(h1, h2, h3, h4) {
    font-family: "JetBrains Mono", monospace;
    font-weight: 600;
  }
  :global(h1) { font-size: 2.5rem; letter-spacing: -0.02em; }
  :global(h2) { font-size: 1.75rem; margin-bottom: 1rem; }
  :global(h3) { font-size: 1.25rem; margin-bottom: 0.5rem; }
  :global(a) { color: #22d3ee; text-decoration: none; }
  :global(a:hover) { text-decoration: underline; }
  :global(p) { margin-bottom: 1rem; color: #94a3b8; }
  :global(code) {
    font-family: "JetBrains Mono", monospace;
    background: rgba(30, 41, 59, 0.5);
    padding: 0.15em 0.4em;
    border-radius: 4px;
    font-size: 0.9em;
  }
  :global(pre) {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 1.25rem;
    overflow-x: auto;
    margin-bottom: 1.5rem;
  }
  :global(pre code) { background: none; padding: 0; }
  :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1.5rem;
  }
  :global(th) {
    text-align: left;
    padding: 0.75rem 1rem;
    background: rgba(30, 41, 59, 0.5);
    border-bottom: 1px solid #1e293b;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.85rem;
    color: #22d3ee;
  }
  :global(td) {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #1e293b;
    font-size: 0.9rem;
  }
  :global(tr:hover) { background: rgba(30, 41, 59, 0.2); }

  header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(2, 6, 23, 0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #1e293b;
  }
  .header-inner {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.5rem;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: "JetBrains Mono", monospace;
    font-weight: 700;
    font-size: 1.25rem;
    color: #e2e8f0;
    text-decoration: none;
  }
  .logo-icon { color: #22d3ee; font-size: 1.4rem; }
  .logo:hover { text-decoration: none; }

  nav { display: flex; gap: 0.25rem; align-items: center; }
  nav a {
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #94a3b8;
    transition: all 0.15s;
  }
  nav a:hover { background: rgba(30, 41, 59, 0.5); color: #e2e8f0; text-decoration: none; }
  nav a.active { background: rgba(34, 211, 238, 0.1); color: #22d3ee; }
  .gh-link {
    margin-left: 0.5rem;
    border: 1px solid #1e293b;
    padding: 0.35rem 0.75rem;
    border-radius: 6px;
  }
  .mobile-toggle {
    display: none;
    background: none;
    border: 1px solid #1e293b;
    color: #e2e8f0;
    font-size: 1.25rem;
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    cursor: pointer;
  }

  main { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; min-height: calc(100vh - 140px); }

  footer {
    border-top: 1px solid #1e293b;
    padding: 2rem 1.5rem;
    text-align: center;
    color: #64748b;
    font-size: 0.85rem;
  }
  .footer-inner a { color: #94a3b8; }

  @media (max-width: 768px) {
    .mobile-toggle { display: block; }
    nav {
      display: none;
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      flex-direction: column;
      background: rgba(2, 6, 23, 0.98);
      border-bottom: 1px solid #1e293b;
      padding: 0.5rem;
    }
    nav.open { display: flex; }
    nav a { padding: 0.6rem 0.75rem; }
    .gh-link { margin-left: 0; }
    :global(h1) { font-size: 1.75rem; }
  }
</style>
