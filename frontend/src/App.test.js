import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const documentResult = {
  source_text: "日本語の文書",
  translated_text: "Japanese document",
  vocabulary: [],
  translation_status: "complete",
  pages_processed: 1,
  target_lang: "en",
};
function upload(name = "report.pdf") {
  fireEvent.change(screen.getByLabelText("Upload Japanese document"), {
    target: { files: [new File(["document"], name)] },
  });
}
afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
});

test("starts with a usable empty workspace and disabled submit", () => {
  render(<App />);
  expect(
    screen.getByRole("button", { name: "Translate document" }),
  ).toBeDisabled();
  expect(
    screen.getByText("From Japanese to your language."),
  ).toBeInTheDocument();
});

test("rejects unsupported uploads", () => {
  render(<App />);
  upload("malware.exe");
  expect(screen.getByRole("alert")).toHaveTextContent("Choose a PDF");
  expect(
    screen.getByRole("button", { name: "Translate document" }),
  ).toBeDisabled();
});

test("processes a document and shows both texts", async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValue({ ok: true, json: async () => documentResult });
  render(<App />);
  upload();
  fireEvent.click(screen.getByRole("button", { name: "Translate document" }));
  expect(await screen.findByText("Japanese document")).toBeInTheDocument();
  expect(screen.getByText("日本語の文書")).toBeInTheDocument();
  expect(global.fetch.mock.calls[0][1].body.get("mode")).toBe("document");
});

test("handles non-JSON server errors", async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 502,
    json: async () => {
      throw new Error();
    },
  });
  render(<App />);
  upload();
  fireEvent.click(screen.getByRole("button", { name: "Translate document" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("502");
});

test("stopped requests cannot overwrite the workspace", async () => {
  let resolve;
  global.fetch = jest.fn(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  render(<App />);
  upload();
  fireEvent.click(screen.getByRole("button", { name: "Translate document" }));
  fireEvent.click(screen.getByRole("button", { name: "Stop waiting" }));
  fireEvent.click(screen.getByRole("button", { name: "New document" }));
  resolve({ ok: true, json: async () => documentResult });
  await waitFor(() =>
    expect(
      screen.getByText("From Japanese to your language."),
    ).toBeInTheDocument(),
  );
  expect(screen.queryByText("Japanese document")).not.toBeInTheDocument();
});

test("vocabulary can be searched and filtered", async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      ...documentResult,
      vocabulary: [
        {
          word: "学校",
          reading: "がっこう",
          pos: "名詞",
          english: ["school"],
          jlpt: "N5",
        },
        {
          word: "経済",
          reading: "けいざい",
          pos: "名詞",
          english: ["economy"],
          jlpt: "N3",
        },
      ],
    }),
  });
  render(<App />);
  upload();
  fireEvent.change(screen.getByLabelText("Output"), {
    target: { value: "vocabulary" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract vocabulary" }));
  await screen.findByText("school");
  fireEvent.change(screen.getByLabelText("Search vocabulary"), {
    target: { value: "economy" },
  });
  expect(screen.queryByText("school")).not.toBeInTheDocument();
  expect(screen.getByText("economy")).toBeInTheDocument();
});
