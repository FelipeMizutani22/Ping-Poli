import { useCallback, useEffect, useState } from "react";

// Busca dados ao montar a tela (e quando `deps` mudam). Devolve { dados, carregando, erro, recarregar }.
export function useApi(funcao, deps = []) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const executar = useCallback(funcao, deps);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await executar());
    } catch (e) {
      setErro(e);
    } finally {
      setCarregando(false);
    }
  }, [executar]);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  return { dados, carregando, erro, recarregar };
}
