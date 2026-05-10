(function () {
  "use strict";

  // --- 1. НАСТРОЙКИ (идентичны main.py) ---
  const WIDTH = 400, HEIGHT = 600;
  const FPS = 60;
  const GRAVITY = 0.5;
  const JUMP_FORCE = -15;
  const FINISH_SCORE = 8000;

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";

  // --- Загрузка ресурсов ---
  const ASSET_BASE = "assets/";
  function loadImg(name) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = ASSET_BASE + name;
    });
  }

  // --- Ввод ---
  const keys = { left: false, right: false };
  let mousePressed = false;
  let mouseX = 0;

  function setKey(code, val) {
    if (code === "ArrowLeft" || code === "KeyA") keys.left = val;
    if (code === "ArrowRight" || code === "KeyD") keys.right = val;
  }
  window.addEventListener("keydown", (e) => { setKey(e.code, true); });
  window.addEventListener("keyup",   (e) => { setKey(e.code, false); });

  function getCanvasX(clientX) {
    const r = canvas.getBoundingClientRect();
    return (clientX - r.left) * (WIDTH / r.width);
  }
  canvas.addEventListener("mousedown", (e) => { mousePressed = true;  mouseX = getCanvasX(e.clientX); canvas.focus(); });
  canvas.addEventListener("mousemove", (e) => { if (mousePressed) mouseX = getCanvasX(e.clientX); });
  window.addEventListener("mouseup",   ()  => { mousePressed = false; });
  canvas.addEventListener("touchstart", (e) => {
    e.preventDefault();
    mousePressed = true;
    mouseX = getCanvasX(e.touches[0].clientX);
  }, { passive: false });
  canvas.addEventListener("touchmove", (e) => {
    e.preventDefault();
    if (e.touches[0]) mouseX = getCanvasX(e.touches[0].clientX);
  }, { passive: false });
  canvas.addEventListener("touchend", (e) => { e.preventDefault(); mousePressed = false; }, { passive: false });

  // --- Утилиты ---
  function randInt(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }
  function rectsCollide(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
  }

  // --- Классы ---
  function Player() {
    this.x = 185; this.y = 450; this.w = 30; this.h = 30;
    this.dy = 0;
  }
  Player.prototype.rect = function () { return { x: this.x, y: this.y, w: this.w, h: this.h }; };
  Player.prototype.move = function () {
    this.dy += GRAVITY;
    this.y += this.dy;

    const mouseLeft  = mousePressed && mouseX <  WIDTH / 2;
    const mouseRight = mousePressed && mouseX >= WIDTH / 2;
    if (keys.left  || mouseLeft)  this.x -= 7;
    if (keys.right || mouseRight) this.x += 7;

    // Оригинал: if self.rect.left > WIDTH: self.rect.right = 0
    if (this.x > WIDTH) this.x = -this.w;
    if (this.x + this.w < 0) this.x = WIDTH;
  };

  function Enemy(y, season) {
    this.w = 60; this.h = 60;
    this.x = randInt(0, WIDTH - this.w); this.y = y;
    this.type = season;
    this.speed = randInt(2, 4);
    this.direction = Math.random() > 0.5 ? 1 : -1;
  }
  Enemy.prototype.update = function () {
    this.x += this.speed * this.direction;
    if (this.x + this.w >= WIDTH || this.x <= 0) this.direction *= -1;
  };
  Enemy.prototype.rect = function () { return { x: this.x, y: this.y, w: this.w, h: this.h }; };

  function Coin(px, py) {
    this.x = px + 7; this.y = py - 50; this.w = 45; this.h = 45;
  }
  Coin.prototype.rect = function () { return { x: this.x, y: this.y, w: this.w, h: this.h }; };

  // --- Запуск ---
  Promise.all([
    loadImg("autumn.png"),
    loadImg("winter.png"),
    loadImg("spring.png"),
    loadImg("doodler.png"),
    loadImg("coin.png"),
    loadImg("enemy_autumn.png"),
    loadImg("enemy_winter.png"),
    loadImg("enemy_spring.png"),
  ]).then(([bgAutumn, bgWinter, bgSpring, doodleImg, coinImg, enA, enW, enS]) => {
    const enemyImgs = { autumn: enA, winter: enW, spring: enS };

    let player = new Player();
    const startPlatform = { x: 170, y: 530, w: 60, h: 10 };
    let platforms = [startPlatform];
    for (let i = 1; i < 7; i++) {
      platforms.push({ x: randInt(0, WIDTH - 60), y: i * 80, w: 60, h: 10 });
    }
    let enemies = [], coins = [];
    let score = 0, coinCount = 0;
    let gameWon = false, running = true;

    function reset() {
      player = new Player();
      score = 0;
      enemies = [];
      coins = [];
      // Пересоздаём платформы: стартовая — гарантированно под игроком,
      // остальные — равномерно вверх с шагом 80, чтобы все были достижимы
      // (max прыжок = JUMP_FORCE^2 / (2*GRAVITY) ≈ 225px).
      platforms = [{ x: player.x - 15, y: player.y + player.h + 5, w: 60, h: 10 }];
      for (let i = 1; i < 7; i++) {
        platforms.push({ x: randInt(0, WIDTH - 60), y: i * 80, w: 60, h: 10 });
      }
    }

    const frameInterval = 1000 / FPS;
    let last = performance.now();
    let acc = 0;

    function loop(now) {
      if (!running) return;
      const delta = now - last;
      last = now;
      acc += delta;
      while (acc >= frameInterval) {
        step();
        acc -= frameInterval;
      }
      draw();
      requestAnimationFrame(loop);
    }

    function step() {
      if (gameWon) return;

      player.move();

      // Коллизия с платформами (только при падении)
      const pr = player.rect();
      for (const p of platforms) {
        if (rectsCollide(pr, p) && player.dy > 0) {
          if (pr.y + pr.h <= p.y + p.h + 10) {
            player.dy = JUMP_FORCE;
          }
        }
      }

      // Сбор монет
      const pr2 = player.rect();
      for (let i = coins.length - 1; i >= 0; i--) {
        if (rectsCollide(pr2, coins[i].rect())) {
          coinCount++;
          coins.splice(i, 1);
        }
      }

      // Враги: движение + столкновение
      for (const en of enemies) en.update();
      for (const en of enemies) {
        if (rectsCollide(player.rect(), en.rect())) {
          reset();
          break;
        }
      }

      // Скролл камеры вверх
      if (player.y < 200) {
        const diff = 200 - player.y;
        player.y = 200;
        score += diff;

        for (const p of platforms) {
          p.y += diff;
          if (p.y > HEIGHT) {
            if (score < FINISH_SCORE) {
              p.y = 0;
              p.x = randInt(0, WIDTH - 60);
              const r = Math.random();
              if (r < 0.10) {
                enemies.push(new Enemy(p.y - 60, currentSeason()));
              } else if (r < 0.20) {
                // оригинал: elif random.random() < 0.20 — независимый roll,
                // но в pygame коде это два отдельных random.random() — здесь
                // используем один `r`, чтобы не было случая "враг И монета".
                coins.push(new Coin(p.x, p.y));
              }
            } else {
              p.y = -100;
            }
          }
        }
        for (const en of enemies) en.y += diff;
        for (const c of coins)   c.y += diff;
        enemies = enemies.filter((en) => en.y < HEIGHT + 100);
        coins   = coins.filter((c) => c.y < HEIGHT + 100);
      }

      // Победа
      if (score >= FINISH_SCORE && platforms.filter((p) => p.y > 0).length === 0) {
        gameWon = true;
      }
      // Падение вниз = reset
      if (player.y > HEIGHT) reset();
    }

    function currentSeason() {
      if (score < 2500)  return "autumn";
      if (score < 5500)  return "winter";
      return "spring";
    }

    function currentBg() {
      if (score < 2500) return bgAutumn;
      if (score < 5500) return bgWinter;
      return bgSpring;
    }

    function txtColor() {
      if (score < 2500) return "rgb(255,255,255)";
      if (score < 5500) return "rgb(0,0,100)";
      return "rgb(0,80,0)";
    }

    function drawText(text, x, y, color) {
      ctx.fillStyle = color;
      ctx.font = "bold 24px sans-serif";
      ctx.textBaseline = "top";
      ctx.fillText(text, x, y);
    }

    function draw() {
      const bg = currentBg();
      if (bg) {
        ctx.drawImage(bg, 0, 0, WIDTH, HEIGHT);
      } else {
        ctx.fillStyle = "rgb(200,200,200)";
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
      }

      // Платформы
      ctx.fillStyle = "rgb(120,120,120)";
      for (const p of platforms) ctx.fillRect(p.x, p.y, p.w, p.h);

      // Монеты
      for (const c of coins) {
        if (coinImg) ctx.drawImage(coinImg, c.x, c.y, c.w, c.h);
        else {
          ctx.fillStyle = "rgb(255,215,0)";
          ctx.beginPath();
          ctx.arc(c.x + c.w / 2, c.y + c.h / 2, 20, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Враги
      for (const en of enemies) {
        const img = enemyImgs[en.type];
        if (img) ctx.drawImage(img, en.x, en.y, en.w, en.h);
        else {
          ctx.fillStyle = "rgb(200,0,0)";
          ctx.beginPath();
          ctx.arc(en.x + en.w / 2, en.y + en.h / 2, 20, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Игрок
      if (doodleImg) ctx.drawImage(doodleImg, player.x, player.y, player.w, player.h);
      else {
        ctx.fillStyle = "rgb(0,200,0)";
        ctx.fillRect(player.x, player.y, player.w, player.h);
      }

      // HUD
      drawText("Height: " + Math.floor(score), 15, 15, txtColor());
      drawText("Coins: " + coinCount, 15, 45, "rgb(255,215,0)");

      if (gameWon) {
        drawText("WIN! ALL SEASONS DONE!", WIDTH / 2 - 140, HEIGHT / 2, "rgb(255,0,0)");
      }
    }

    canvas.focus();
    requestAnimationFrame((t) => { last = t; loop(t); });
  });
})();
