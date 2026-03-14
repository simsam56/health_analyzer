"use client";

interface ErrorCardProps {
  message?: string;
}

export function ErrorCard({
  message = "Erreur de connexion à l\u2019API. V\u00e9rifiez que le serveur tourne sur le port 8765.",
}: ErrorCardProps) {
  return (
    <div className="glass rounded-2xl p-6 text-center text-accent-red">
      {message}
    </div>
  );
}
