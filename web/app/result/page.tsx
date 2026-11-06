import { Suspense } from "react";
import { ResultView } from "@/components/ResultView";

export default function ResultPage() {
  return (
    <Suspense>
      <ResultView />
    </Suspense>
  );
}
