class TextType {
  constructor(elementSelector, options = {}) {
    this.element = document.querySelector(elementSelector);

    this.texts = options.texts || ["Welcome"];
    this.typingSpeed = options.typingSpeed || 60;
    this.deletingSpeed = options.deletingSpeed || 40;
    this.pauseDuration = options.pauseDuration || 1500;
    this.loop = options.loop !== undefined ? options.loop : true;

    this.showCursor = options.showCursor !== false;
    this.cursorCharacter = options.cursorCharacter || "|";

    this.textIndex = 0;
    this.charIndex = 0;
    this.isDeleting = false;

    this.init();
  }

  init() {
    this.element.innerHTML = `<span class="tt-text"></span>${
      this.showCursor
        ? `<span class="tt-cursor">${this.cursorCharacter}</span>`
        : ""
    }`;
    this.textSpan = this.element.querySelector(".tt-text");
    this.cursorSpan = this.element.querySelector(".tt-cursor");

    this.type();
    this.cursorBlink();
  }

  cursorBlink() {
    if (!this.showCursor) return;

    setInterval(() => {
      this.cursorSpan.classList.toggle("tt-cursor-hidden");
    }, 500);
  }

  type() {
    const currentText = this.texts[this.textIndex];

    if (this.isDeleting) {
      this.textSpan.textContent = currentText.substring(0, this.charIndex - 1);
      this.charIndex--;
    } else {
      this.textSpan.textContent = currentText.substring(0, this.charIndex + 1);
      this.charIndex++;
    }

    let speed = this.isDeleting ? this.deletingSpeed : this.typingSpeed;

    if (!this.isDeleting && this.charIndex === currentText.length) {
      if (!this.loop && this.textIndex === this.texts.length - 1) return;
      speed = this.pauseDuration;
      this.isDeleting = true;
    } else if (this.isDeleting && this.charIndex === 0) {
      this.isDeleting = false;
      this.textIndex = (this.textIndex + 1) % this.texts.length;
      speed = 500;
    }

    setTimeout(() => this.type(), speed);
  }
}
