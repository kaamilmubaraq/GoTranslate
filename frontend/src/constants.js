export const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "zh-CN", label: "Chinese" },
  { value: "ko", label: "Korean" },
  { value: "th", label: "Thai" },
  { value: "lo", label: "Lao" },
  { value: "mn", label: "Mongolian" },
];
export const POS_LABELS = {
  名詞: "Noun",
  動詞: "Verb",
  形容詞: "Adjective",
  形状詞: "Adjective",
  副詞: "Adverb",
};
export const ACCEPT = ".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff";
export const MAX_BYTES = 20 * 1024 * 1024;
export function validateFile(file) {
  if (!file) return "";
  if (!/\.(pdf|jpe?g|png|webp|bmp|tiff?)$/i.test(file.name))
    return "Choose a PDF, JPG, PNG, WebP, BMP, or TIFF file.";
  if (file.size === 0) return "This file is empty. Choose a file with content.";
  if (file.size > MAX_BYTES)
    return "This file is too large. Choose a file under 20 MB.";
  return "";
}
