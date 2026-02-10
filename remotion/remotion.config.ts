import { Config } from "@remotion/cli/config";

Config.setBrowserExecutable(
  "/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome"
);
Config.setChromiumHeadlessMode("new");
