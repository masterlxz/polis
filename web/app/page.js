import { redirect } from "next/navigation";

// Provisório (307): a raiz leva à busca até existir uma página inicial.
export default function Raiz() {
  redirect("/busca/");
}
