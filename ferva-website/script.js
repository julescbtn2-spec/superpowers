'use strict';

/* ═══════════════ DATA ═══════════════════════════════════════ */
const FLAVORS = [
  // Grande Surface
  { name:'Citron\nGingembre',    desc:'Frais et pétillant, avec une touche épicée. Une alliance audacieuse entre l\'acidité vive du citron et la chaleur subtile du gingembre frais.',               color:'#D4B84A', rgb:'212,184,74',  type:'Kéfir',    gamme:'Grande Surface',              formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Framboise\nHibiscus',  desc:'Fruité et floral, légèrement acidulé. La framboise sauvage rencontre les notes florales de l\'hibiscus pour une boisson raffinée et lumineuse.',              color:'#C0394B', rgb:'192,57,75',   type:'Kombucha', gamme:'Grande Surface',              formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Pomme\nMenthe',        desc:'Doux et rafraîchissant, finement mentholé. La douceur naturelle de la pomme s\'unit à la fraîcheur herbacée de la menthe pour un équilibre parfait.',         color:'#4E9A6F', rgb:'78,154,111',  type:'Kéfir',    gamme:'Grande Surface',              formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Mangue\nPassion',      desc:'Exotique et gourmand, 100% plaisir. Un voyage tropical à chaque gorgée — la mangue mûre et le fruit de la passion créent une symphonie ensoleillée.',         color:'#E8922A', rgb:'232,146,42',  type:'Kombucha', gamme:'Grande Surface',              formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Citron Vert\nNature',  desc:'Intense et désaltérant. Le classique réinventé. Le citron vert dans toute sa pureté — vif, minéral, intemporel. La référence de la gamme.',                   color:'#7DBF5E', rgb:'125,191,94',  type:'Kéfir',    gamme:'Grande Surface',              formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  // Boulangeries & Restaurants
  { name:'Fraise\nBasilic',      desc:'Fraise juteuse et basilic frais, tout en délicatesse. Un accord gastronomique qui sublime aussi bien l\'apéritif que le dessert.',                            color:'#D4627A', rgb:'212,98,122',  type:'Kéfir',    gamme:'Boulangeries & Restaurants',  formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Pêche\nVerveine',      desc:'Ronde et douce, avec une note herbacée. La pêche de vigne rencontre la verveine citronnelle — une boisson d\'accord parfaite avec les pâtisseries fines.',   color:'#E8A850', rgb:'232,168,80',  type:'Kombucha', gamme:'Boulangeries & Restaurants',  formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Poire\nThym',          desc:'Subtil et aromatique, élégant. La poire Williams et le thym frais composent un duo raffiné, idéal en accord avec les charcuteries et les fromages.',          color:'#A8C870', rgb:'168,200,112', type:'Kéfir',    gamme:'Boulangeries & Restaurants',  formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Citron\nMiel',         desc:'Doux et réconfortant, parfait avec les douceurs. Le citron apporte sa vivacité, le miel sa rondeur — une boisson qui accompagne à merveille viennoiseries et desserts.', color:'#D4A840', rgb:'212,168,64', type:'Kombucha', gamme:'Boulangeries & Restaurants',  formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  { name:'Pamplemousse\nRomarin',desc:'Tonique et raffiné, une amertume maîtrisée. Le pamplemousse rose et le romarin méditerranéen — une alliance sophistiquée qui stimule et désaltère.',            color:'#E87060', rgb:'232,112,96',  type:'Kéfir',    gamme:'Boulangeries & Restaurants',  formats:['25cl','33cl','50cl'], price:'dès <strong>4,20 €</strong>' },
  // Grand Format
  { name:'Citron\nConcombre',    desc:'Léger et hydratant, parfait à table. Le citron et le concombre — deux végétaux aqueux qui s\'associent pour une boisson d\'une fraîcheur absolue à partager.',color:'#6EC49A', rgb:'110,196,154', type:'Kéfir',    gamme:'Grand Format Particuliers',   formats:['75cl','1L'],           price:'dès <strong>8,50 €</strong>' },
  { name:'Myrtille\nLavande',    desc:'Floral et fruité, douceur et profondeur. La myrtille sauvage et la lavande de Provence composent un accord unique — à la fois délicat, intense et mémorable.',  color:'#8B6EC8', rgb:'139,110,200', type:'Kombucha', gamme:'Grand Format Particuliers',   formats:['75cl','1L'],           price:'dès <strong>8,50 €</strong>' },
  { name:'Gingembre\nCurcuma',   desc:'Épicé et revigorant, effet naturel. Le gingembre et le curcuma — deux racines aux vertus reconnues — forment une boisson chaleureuse et dynamisante.',         color:'#D48A20', rgb:'212,138,32',  type:'Kéfir',    gamme:'Grand Format Particuliers',   formats:['75cl','1L'],           price:'dès <strong>8,50 €</strong>' },
  { name:'Ananas\nMenthe',       desc:'Tropical et rafraîchissant, ensoleillé. L\'ananas Victoria apporte sa douceur exotique, la menthe sa fraîcheur — une boisson de table lumineuse et conviviale.',color:'#4AB870', rgb:'74,184,112',  type:'Kombucha', gamme:'Grand Format Particuliers',   formats:['75cl','1L'],           price:'dès <strong>8,50 €</strong>' },
  { name:'Cassis Baies\nde Sureau',desc:'Profond et gourmand, riche en antioxydants. Le cassis noir et les baies de sureau de nos prairies — une boisson intense, veloutée, aux vertus précieuses.',  color:'#7A3A9A', rgb:'122,58,154',  type:'Kombucha', gamme:'Grand Format Particuliers',   formats:['75cl','1L'],           price:'dès <strong>8,50 €</strong>' },
];

/* ═══════════════ STATE ══════════════════════════════════════ */
let activeIndex  = 0;
let cycleTimer   = null;
let cycleRunning = false;
let progressVal  = 0;
let progressRaf  = null;
const CYCLE_MS   = 4000;

/* ═══════════════ DOM REFS ═══════════════════════════════════ */
const root       = document.documentElement;
const navEl      = document.getElementById('nav');
const navLinks   = document.getElementById('navLinks');
const burger     = document.getElementById('burger');
const navPulse   = document.getElementById('navPulse');
const flItems    = Array.from(document.querySelectorAll('.fl-item'));
const dName      = document.getElementById('dName');
const dDesc      = document.getElementById('dDesc');
const dType      = document.getElementById('dType');
const dGamme     = document.getElementById('dGamme');
const dFormats   = document.getElementById('dFormats');
const dPrice     = document.getElementById('dPrice');
const flOrb      = document.getElementById('flavorOrb');
const progressBar= document.getElementById('flProgressBar');
const ticker     = document.getElementById('tickerTrack');
const faqItems   = document.querySelectorAll('.faq-item');

/* ═══════════════ ACCENT COLOR ══════════════════════════════ */
function setAccent(color, rgb) {
  root.style.setProperty('--accent', color);
  root.style.setProperty('--accent-rgb', rgb);
}

/* ═══════════════ FLAVOR PICKER ═════════════════════════════ */
function setFlavor(index, auto) {
  const f = FLAVORS[index];
  activeIndex = index;

  // Accent color
  setAccent(f.color, f.rgb);

  // Nav pulse
  if (navPulse) navPulse.style.background = f.color;

  // Orb
  if (flOrb) {
    flOrb.style.background = `radial-gradient(circle, ${f.color}, transparent 65%)`;
  }

  // Display — fade trick
  if (dName) {
    dName.style.opacity = '0';
    setTimeout(() => {
      dName.innerHTML  = f.name.replace('\n', '<br>');
      dName.style.opacity = '1';
      dName.style.transition = 'opacity 0.3s';
    }, 150);
  }
  if (dDesc)    dDesc.textContent    = f.desc;
  if (dType)    dType.textContent    = f.type;
  if (dGamme)   dGamme.textContent   = f.gamme;
  if (dPrice)   dPrice.innerHTML     = `dès ${f.price}`;

  if (dFormats) {
    dFormats.innerHTML = f.formats.map(s => `<span>${s}</span>`).join('');
  }

  // Active state in list
  flItems.forEach((el, i) => el.classList.toggle('active', i === index));

  // Scroll item into view (within the list)
  if (flItems[index]) {
    flItems[index].scrollIntoView({ block:'nearest', behavior:'smooth' });
  }

  // Progress bar reset
  resetProgress();
}

/* ═══════════════ AUTO-CYCLE ════════════════════════════════ */
function resetProgress() {
  cancelAnimationFrame(progressRaf);
  progressVal = 0;
  if (progressBar) progressBar.style.width = '0%';
  if (cycleRunning) animateProgress();
}

function animateProgress() {
  const start = performance.now();
  function step(now) {
    progressVal = Math.min(((now - start) / CYCLE_MS) * 100, 100);
    if (progressBar) progressBar.style.width = progressVal + '%';
    if (progressVal < 100) {
      progressRaf = requestAnimationFrame(step);
    } else {
      const next = (activeIndex + 1) % FLAVORS.length;
      setFlavor(next, true);
    }
  }
  progressRaf = requestAnimationFrame(step);
}

function startCycle() {
  if (cycleRunning) return;
  cycleRunning = true;
  animateProgress();
}

function stopCycle() {
  cycleRunning = false;
  cancelAnimationFrame(progressRaf);
  if (progressBar) progressBar.style.width = '0%';
}

// Flavor list click
flItems.forEach((btn, i) => {
  btn.addEventListener('click', () => {
    stopCycle();
    setFlavor(i, false);
  });
});

// Pause on hover display, resume on leave
const flDisplay = document.getElementById('flavorDisplay');
if (flDisplay) {
  flDisplay.addEventListener('mouseenter', stopCycle);
  flDisplay.addEventListener('mouseleave', startCycle);
  const flList = document.getElementById('flavorList');
  if (flList) {
    flList.addEventListener('mouseenter', stopCycle);
    flList.addEventListener('mouseleave', startCycle);
  }
}

/* ═══════════════ NAV ════════════════════════════════════════ */
const onScroll = () => navEl.classList.toggle('scrolled', window.scrollY > 60);
window.addEventListener('scroll', onScroll, { passive:true });
onScroll();

burger.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  burger.classList.toggle('open', open);
  burger.setAttribute('aria-expanded', open);
  document.body.style.overflow = open ? 'hidden' : '';
});

navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    navLinks.classList.remove('open');
    burger.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  });
});

/* ═══════════════ TICKER DUPLICATE ══════════════════════════ */
if (ticker) {
  ticker.innerHTML += ticker.innerHTML;
}

/* ═══════════════ FAQ ACCORDION ═════════════════════════════ */
faqItems.forEach(item => {
  const btn = item.querySelector('.faq-q');
  btn.addEventListener('click', () => {
    const wasOpen = item.classList.contains('open');
    faqItems.forEach(i => i.classList.remove('open'));
    if (!wasOpen) item.classList.add('open');
  });
});

/* ═══════════════ FORMS ══════════════════════════════════════ */
function handleForm(formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  let msg = form.nextElementSibling;
  if (!msg || !msg.classList.contains('form-success-msg')) {
    msg = document.createElement('p');
    msg.className = 'form-success-msg';
    msg.textContent = 'Message envoyé ! Nous revenons vers vous sous 48h.';
    form.after(msg);
  }

  form.addEventListener('submit', e => {
    e.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Envoi en cours…';
    setTimeout(() => {
      form.reset();
      btn.disabled = false;
      btn.textContent = btn.dataset.label || 'Envoyer';
      msg.classList.add('show');
      setTimeout(() => msg.classList.remove('show'), 6000);
    }, 1000);
  });
}

handleForm('prosForm');
handleForm('investForm');

// Store original button labels
document.querySelectorAll('button[type=submit]').forEach(btn => {
  btn.dataset.label = btn.textContent.trim();
});

/* ═══════════════ SCROLL REVEAL ═════════════════════════════ */
const revealObs = new IntersectionObserver(entries => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      const delay = entry.target.dataset.delay || (i * 80);
      setTimeout(() => entry.target.classList.add('revealed'), Number(delay));
      revealObs.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('[data-reveal]').forEach((el, i) => {
  el.dataset.delay = el.dataset.delay || String(i * 60);
  revealObs.observe(el);
});

/* ═══════════════ SMOOTH ANCHORS ════════════════════════════ */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      const top = target.getBoundingClientRect().top + window.scrollY - navEl.offsetHeight - 16;
      window.scrollTo({ top, behavior:'smooth' });
    }
  });
});

/* ═══════════════ INIT ═══════════════════════════════════════ */
setFlavor(0, false);
startCycle();
