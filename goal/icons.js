const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FaTree,
  FaSeedling,
  FaCrown,
  FaFistRaised,
  FaBalanceScale,
} = require("react-icons/fa");

const ICON_MAP = {
  tree: FaTree,
  seedling: FaSeedling,
  crown: FaCrown,
  fist: FaFistRaised,
  balance: FaBalanceScale,
};

async function renderIcon(name, color = "#FFFFFF", size = 256) {
  const Comp = ICON_MAP[name];
  if (!Comp) throw new Error("Unknown icon: " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { size, color })
  );
  const buf = await sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

module.exports = { renderIcon };
