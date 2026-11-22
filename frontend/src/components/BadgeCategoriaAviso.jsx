import { Badge } from "react-bootstrap";

import { CORES_CATEGORIA_AVISO, rotulo } from "../utils/rotulos";

// Etiqueta colorida da categoria do aviso (UC06). Usada no quadro, no detalhe e na página inicial.
export default function BadgeCategoriaAviso({ categoria }) {
  return <Badge bg={CORES_CATEGORIA_AVISO[categoria] || "secondary"}>{rotulo("categoriaAviso", categoria)}</Badge>;
}
