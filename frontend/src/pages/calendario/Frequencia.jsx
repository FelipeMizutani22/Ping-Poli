import { Button } from "react-bootstrap";
import { Link } from "react-router-dom";

import PaginaProvisoria from "../../components/PaginaProvisoria";
import { useAuth } from "../../contexts/AuthContext";

// O relatório de frequência (UC11) é a C10. Por enquanto, daqui o Diretor chega ao ajuste de presenças (UC10).
export default function Frequencia() {
  const { ehDiretor } = useAuth();
  return (
    <>
      {ehDiretor && (
        <div className="d-flex justify-content-end mb-3">
          <Button as={Link} to="/frequencia/ajustar">Ajustar presenças</Button>
        </div>
      )}
      <PaginaProvisoria titulo="Frequência" uc="UC11" />
    </>
  );
}
