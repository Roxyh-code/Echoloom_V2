import { redirect } from "next/navigation";
export default function Page() {
  redirect("/rehearsal?view=characters&create=1");
}
