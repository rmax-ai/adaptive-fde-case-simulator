import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";

const isDev = process.argv.includes("dev");

export default {
  plugins: [sveltekit()],
  kit: {
    adapter: adapter({
      pages: "build",
      assets: "build",
      fallback: "404.html",
      precompress: false,
      strict: true,
    }),
    paths: {
      base: isDev ? "" : (process.env.BASE_PATH ?? ""),
    },
  },
};
