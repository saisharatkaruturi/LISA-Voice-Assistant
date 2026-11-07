const pptxgen = require("pptxgenjs");
const path = require("path");
const { renderIcon } = require("./icons.js");
const { applyTheme } = require(
  "C:\\Users\\shara\\.claude\\skills\\synced\\e8e2d261-9881-4b02-a20d-a380b4ce4673_edf445fe-d093-4b36-8037-2d5780011881\\pptx\\scripts\\apply_theme.js"
);

const THEME = {
  name: "Senju Legacy",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1A1A",
    lt1: "FFFFFF",
    dk2: "2D6A4F",
    lt2: "E9F0EA",
    accent1: "D4AF37", // gold - legendary / God of Shinobi
    accent2: "1B4332", // deep forest - dark hero backgrounds
    accent3: "74A57F", // sage green - secondary
    accent4: "4A6670", // slate blue-grey - Tobirama's tone
    accent5: "8C6A1E", // dark gold
    accent6: "3A5A40", // olive
    hlink: "D4AF37",
    folHlink: "8C6A1E",
  },
};

const OUT = path.join(__dirname, "Hashirama_vs_Tobirama.pptx");

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.company = "Senju Legacy";

  const C = pres.SchemeColor;

  const iconTree = await renderIcon("tree");
  const iconSeedling = await renderIcon("seedling");
  const iconCrown = await renderIcon("crown");
  const iconFist = await renderIcon("fist");
  const iconBalance = await renderIcon("balance");

  function addIconCircle(slide, { x, y, d, bg, icon, iconScale = 0.52 }) {
    slide.addShape(pres.ShapeType.ellipse, {
      x, y, w: d, h: d,
      fill: { color: bg },
      line: { type: "none" },
    });
    const id = d * iconScale;
    slide.addImage({ data: icon, x: x + (d - id) / 2, y: y + (d - id) / 2, w: id, h: id });
  }

  function addDecoCircle(slide, { x, y, d, color, transparency = 70 }) {
    slide.addShape(pres.ShapeType.ellipse, {
      x, y, w: d, h: d,
      fill: { color, transparency },
      line: { type: "none" },
    });
  }

  function addIconCard(slide, { x, y, w, icon, iconBg, title, desc }) {
    const d = 0.9;
    addIconCircle(slide, { x: x + w / 2 - d / 2, y, d, bg: iconBg, icon });
    slide.addText(title, {
      x, y: y + d + 0.15, w, h: 0.4,
      fontFace: THEME.headFontFace, fontSize: 15, bold: true,
      color: THEME.colors.dk1, align: "center", valign: "top", margin: 0, isTextBox: true,
    });
    slide.addText(desc, {
      x, y: y + d + 0.6, w, h: 1.3,
      fontFace: THEME.bodyFontFace, fontSize: 12,
      color: "555555", align: "center", valign: "top", margin: 0, isTextBox: true,
    });
  }

  function addStatCard(slide, { x, y, w, big, label }) {
    slide.addText(big, {
      x, y, w, h: 0.9,
      fontFace: THEME.headFontFace, fontSize: 40, bold: true,
      color: THEME.colors.accent5, align: "center", valign: "bottom", margin: 0, isTextBox: true,
    });
    slide.addText(label, {
      x, y: y + 0.95, w, h: 0.75,
      fontFace: THEME.bodyFontFace, fontSize: 12,
      color: "555555", align: "center", valign: "top", margin: 0, isTextBox: true,
    });
  }

  function addBullets(slide, items, opts) {
    const paras = items.map((t, i) => ({
      text: t,
      options: {
        bullet: { code: "25AA", indent: 18 },
        color: THEME.colors.dk1,
        breakLine: i < items.length - 1,
        paraSpaceAfter: 12,
      },
    }));
    slide.addText(paras, Object.assign({
      fontFace: THEME.bodyFontFace, fontSize: 14, align: "left", valign: "top",
      margin: 0, isTextBox: true, lineSpacingMultiple: 1.15,
    }, opts));
  }

  // =====================================================================
  // LAYOUTS
  // =====================================================================

  pres.defineSlideMaster({
    title: "TITLE",
    background: { color: THEME.colors.accent2 },
    objects: [
      {
        placeholder: {
          options: {
            name: "title", type: "title",
            x: 0.8, y: 2.5, w: 11.4, h: 1.5,
            fontFace: THEME.headFontFace, fontSize: 48, bold: true,
            color: C.background1, align: "left", valign: "top", margin: 0,
          },
          text: "",
        },
      },
      {
        placeholder: {
          options: {
            name: "subtitle", type: "body",
            x: 0.8, y: 4.05, w: 10.6, h: 0.8,
            fontFace: THEME.bodyFontFace, fontSize: 18,
            color: C.accent1, align: "left", valign: "top", margin: 0,
          },
          text: "",
        },
      },
    ],
  });

  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: THEME.colors.lt1 },
    objects: [
      {
        placeholder: {
          options: {
            name: "title", type: "title",
            x: 0.6, y: 0.45, w: 12.1, h: 0.85,
            fontFace: THEME.headFontFace, fontSize: 30, bold: true,
            color: C.text1, align: "left", valign: "top", margin: 0,
          },
          text: "",
        },
      },
      {
        text: {
          text: "HASHIRAMA  vs  TOBIRAMA",
          options: {
            x: 0.6, y: 7.1, w: 6, h: 0.3,
            fontFace: THEME.bodyFontFace, fontSize: 10, color: C.accent3,
            align: "left", margin: 0, isTextBox: true, objectName: "footer",
          },
        },
      },
    ],
  });

  pres.defineSlideMaster({
    title: "CLOSING",
    background: { color: THEME.colors.accent2 },
    objects: [
      {
        placeholder: {
          options: {
            name: "title", type: "title",
            x: 0.8, y: 0.9, w: 11.4, h: 1.0,
            fontFace: THEME.headFontFace, fontSize: 40, bold: true,
            color: C.background1, align: "left", valign: "top", margin: 0,
          },
          text: "",
        },
      },
      {
        placeholder: {
          options: {
            name: "subtitle", type: "body",
            x: 0.8, y: 1.95, w: 11.0, h: 0.9,
            fontFace: THEME.bodyFontFace, fontSize: 18,
            color: C.accent1, align: "left", valign: "top", margin: 0,
          },
          text: "",
        },
      },
    ],
  });

  // =====================================================================
  // SLIDE 1 — TITLE
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "TITLE" });
    addDecoCircle(s, { x: 9.5, y: 4.2, d: 6.5, color: THEME.colors.accent6 });
    s.addText(
      [
        { text: "Hashirama ", options: { color: C.background1 } },
        { text: "> ", options: { color: THEME.colors.accent1 } },
        { text: "Tobirama", options: { color: THEME.colors.accent3 } },
      ],
      { placeholder: "title" }
    );
    s.addText(
      "Seven reasons the First Hokage stands above his brother \u2014 and the Second's legacy, fairly weighed.",
      { placeholder: "subtitle" }
    );
  }

  // =====================================================================
  // SLIDE 2 — THESIS / OVERVIEW
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("The Case, In Brief", { placeholder: "title" });
    s.addText("Four categories. Hashirama leads in every single one.", {
      x: 0.6, y: 1.3, w: 12.1, h: 0.4,
      fontFace: THEME.bodyFontFace, fontSize: 14, italic: true,
      color: "555555", align: "left", valign: "top", margin: 0, isTextBox: true,
    });

    const cardW = 2.8, gap = 0.3, startX = 0.6, cardY = 2.3;
    const cards = [
      { icon: iconFist, title: "Raw Power", desc: "Fought Madara Uchiha to a standstill \u2014 solo." },
      { icon: iconTree, title: "Mokuton", desc: "A kekkei genkai no one else has ever fully wielded." },
      { icon: iconSeedling, title: "Nation Builder", desc: "Grew Konoha's forests and founded the village itself." },
      { icon: iconCrown, title: "The Title Itself", desc: "Shinobi history has only ever named one God." },
    ];
    cards.forEach((c, i) => {
      addIconCard(s, {
        x: startX + i * (cardW + gap), y: cardY, w: cardW,
        icon: c.icon, iconBg: THEME.colors.accent2, title: c.title, desc: c.desc,
      });
    });
  }

  // =====================================================================
  // SLIDE 3 — MOKUTON
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Mokuton: A Bloodline All His Own", { placeholder: "title" });

    addBullets(s, [
      "Fuses two chakra natures \u2014 Earth and Water \u2014 into Wood Release, a kekkei genkai unique to him.",
      "Scales from combat to restraint: a single wood dragon was enough to bind a tailed beast.",
      "Grows full forests on command \u2014 instantly, not over seasons.",
      "No one has ever matched it since. Not Tobirama. Not anyone.",
    ], { x: 0.6, y: 1.75, w: 6.7, h: 4.6 });

    addIconCircle(s, { x: 9.5, y: 2.5, d: 2.3, bg: THEME.colors.accent2, icon: iconTree });
    s.addText("2 Natures \u2192 1 Kekkei Genkai", {
      x: 8.1, y: 5.0, w: 5.1, h: 0.5,
      fontFace: THEME.headFontFace, fontSize: 16, bold: true,
      color: THEME.colors.accent5, align: "center", valign: "top", margin: 0, isTextBox: true,
    });
  }

  // =====================================================================
  // SLIDE 4 — SAGE MODE / NATION BUILDING
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Built a Village, Mastered Sage Mode", { placeholder: "title" });

    const statW = 3.7, statGap = 0.5, statX = 0.9, statY = 1.7;
    const stats = [
      { big: "1,000+", label: "Wood clones fielded in a single battle" },
      { big: "1", label: "Village founded from scratch: Konohagakure" },
      { big: "0", label: "Equals in Senjutsu mastery during his lifetime" },
    ];
    stats.forEach((st, i) => {
      addStatCard(s, { x: statX + i * (statW + statGap), y: statY, w: statW, big: st.big, label: st.label });
    });

    addBullets(s, [
      "Senjutsu control precise enough to reshape terrain mid-battle, growing a forest where there was none.",
      "Chakra reserves so vast that later generations measured \u201cmonster chakra\u201d against his.",
      "Founded Konoha with Tobirama's help \u2014 but the vision, the land, and the living defenses were his.",
    ], { x: 0.9, y: 4.05, w: 11.5, h: 2.8 });
  }

  // =====================================================================
  // SLIDE 5 — GOD OF SHINOBI
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText('Earning the Name \u201cGod of Shinobi\u201d', { placeholder: "title" });

    s.addText(
      '\u201cThe only shinobi who could stand against Madara Uchiha at full strength \u2014 and still be standing after.\u201d',
      {
        x: 0.6, y: 1.75, w: 7.5, h: 1.9,
        fontFace: THEME.headFontFace, fontSize: 24, italic: true, bold: true,
        color: THEME.colors.accent2, align: "left", valign: "top", margin: 0, isTextBox: true,
      }
    );
    addIconCircle(s, { x: 9.0, y: 1.9, d: 2.0, bg: THEME.colors.accent1, icon: iconCrown });

    addBullets(s, [
      "Valley of the End: their clash was so immense it carved the landscape \u2014 still visible generations later.",
      "Fought Madara, wielding the Nine-Tails' power, essentially alone \u2014 and matched him blow for blow.",
      "Named God of Shinobi by his peers: a title no other shinobi, including Tobirama, has ever held.",
    ], { x: 0.6, y: 4.1, w: 12.1, h: 2.6 });
  }

  // =====================================================================
  // SLIDE 6 — TOBIRAMA'S DUE
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CONTENT" });
    s.addText("Fair's Fair: What Tobirama Brought", { placeholder: "title" });
    addIconCircle(s, { x: 0.6, y: 1.55, d: 1.0, bg: THEME.colors.accent4, icon: iconBalance });

    s.addText("Innovator", {
      x: 0.6, y: 2.8, w: 5.6, h: 0.4,
      fontFace: THEME.headFontFace, fontSize: 18, bold: true,
      color: THEME.colors.accent4, align: "left", valign: "top", margin: 0, isTextBox: true,
    });
    addBullets(s, [
      "Created Edo Tensei, one of the most feared forbidden jutsu in history.",
      "Laid the space-time groundwork later perfected into the Flying Raijin.",
      "Founded the Academy system that still trains shinobi generations later.",
    ], { x: 0.6, y: 3.3, w: 5.6, h: 2.3 });

    s.addText("Administrator", {
      x: 6.9, y: 2.8, w: 5.6, h: 0.4,
      fontFace: THEME.headFontFace, fontSize: 18, bold: true,
      color: THEME.colors.accent4, align: "left", valign: "top", margin: 0, isTextBox: true,
    });
    addBullets(s, [
      "Served as Second Hokage, building Konoha's institutions and laws.",
      "Developed formidable water-style and barrier techniques of his own.",
      "A brilliant, disciplined strategist \u2014 by any normal measure, elite.",
    ], { x: 6.9, y: 3.3, w: 5.6, h: 2.3 });

    s.addText(
      "Tobirama built the machine. Hashirama was the force nothing could stop.",
      {
        x: 0.6, y: 6.0, w: 11.9, h: 0.6,
        fontFace: THEME.bodyFontFace, fontSize: 14, italic: true,
        color: "555555", align: "left", valign: "top", margin: 0, isTextBox: true,
      }
    );
  }

  // =====================================================================
  // SLIDE 7 — VERDICT
  // =====================================================================
  {
    const s = pres.addSlide({ masterName: "CLOSING" });
    addDecoCircle(s, { x: -2.5, y: -2.5, d: 5.5, color: THEME.colors.accent6 });

    s.addText("The Verdict", { placeholder: "title" });
    s.addText(
      "Brilliant engineer. Living force of nature. Only one of them is a god.",
      { placeholder: "subtitle" }
    );

    s.addChart(
      pres.ChartType.bar,
      [
        {
          name: "Power Tier",
          labels: ["Hashirama", "Tobirama"],
          values: [96, 74],
        },
      ],
      {
        x: 2.4, y: 3.3, w: 8.5, h: 2.1,
        barDir: "bar",
        showTitle: false,
        showLegend: false,
        showValue: true,
        dataLabelPosition: "outEnd",
        dataLabelColor: THEME.colors.lt1,
        dataLabelFontSize: 14,
        dataLabelFontBold: true,
        chartColors: [THEME.colors.accent1, THEME.colors.accent3],
        catAxisLabelColor: THEME.colors.lt1,
        catAxisLabelFontSize: 14,
        catAxisLineColor: THEME.colors.accent3,
        valAxisHidden: true,
        valGridLine: { style: "none" },
        catGridLine: { style: "none" },
        plotArea: { fill: { color: THEME.colors.accent2 } },
        chartArea: { fill: { color: THEME.colors.accent2 } },
      }
    );

    s.addText(
      "(A completely scientific, highly biased power tier.)",
      {
        x: 2.4, y: 5.55, w: 8.5, h: 0.4,
        fontFace: THEME.bodyFontFace, fontSize: 11, italic: true,
        color: THEME.colors.accent3, align: "center", valign: "top", margin: 0, isTextBox: true,
      }
    );
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("Wrote", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
