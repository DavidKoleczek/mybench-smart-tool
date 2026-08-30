import { useEffect, useState } from "react";

type TaskResult = {
  path: string;
  score: number | null;
  run: {
    task: string;
    model: string;
    status: string;
    finished: string;
  };
};

function App() {
  const [results, setResults] = useState<TaskResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/results")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`The API answered ${response.status}.`);
        }
        return response.json() as Promise<TaskResult[]>;
      })
      .then(setResults)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : String(cause));
      });
  }, []);

  return (
    <main className="mx-auto flex min-h-svh max-w-3xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">MyBench</h1>
      {error !== null && <p className="text-destructive">{error}</p>}
      {results !== null && results.length === 0 && (
        <p className="text-muted-foreground">
          No results yet. Run the benchmark with `mybench run`.
        </p>
      )}
      {results !== null && results.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Task</th>
              <th className="py-2 pr-4 font-medium">Model</th>
              <th className="py-2 pr-4 font-medium">Status</th>
              <th className="py-2 pr-4 font-medium">Score</th>
              <th className="py-2 font-medium">Finished</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.path} className="border-b">
                <td className="py-2 pr-4">{result.run.task}</td>
                <td className="py-2 pr-4">{result.run.model}</td>
                <td className="py-2 pr-4">{result.run.status}</td>
                <td className="py-2 pr-4">{result.score ?? "-"}</td>
                <td className="py-2">
                  {new Date(result.run.finished).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

export default App;
