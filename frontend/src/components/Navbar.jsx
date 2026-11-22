import { Container, Nav, NavDropdown, Navbar as BsNavbar } from "react-bootstrap";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

export default function Navbar() {
  const { usuario, ehDiretor, sair } = useAuth();

  return (
    <BsNavbar expand="lg" variant="dark" className="navbar-pingpoli mb-4">
      <Container>
        <BsNavbar.Brand as={Link} to="/" className="fw-bold">
          Ping<span>Poli</span>
        </BsNavbar.Brand>
        <BsNavbar.Toggle aria-controls="menu-principal" />
        <BsNavbar.Collapse id="menu-principal">
          <Nav className="me-auto">
            <Nav.Link as={NavLink} to="/" end>Início</Nav.Link>
            <Nav.Link as={NavLink} to="/avisos">Avisos</Nav.Link>
            <Nav.Link as={NavLink} to="/calendario">Calendário</Nav.Link>
            <Nav.Link as={NavLink} to="/campeonatos">Campeonatos</Nav.Link>
            <NavDropdown title="Partidas" id="menu-partidas">
              <NavDropdown.Item as={Link} to="/partidas">Minhas partidas</NavDropdown.Item>
              <NavDropdown.Item as={Link} to="/partidas/nova">Registrar partida</NavDropdown.Item>
              <NavDropdown.Item as={Link} to="/partidas/pendentes">Partidas pendentes</NavDropdown.Item>
            </NavDropdown>
            <Nav.Link as={NavLink} to="/desempenho">Desempenho</Nav.Link>
            {ehDiretor && (
              <NavDropdown title="Administração" id="menu-admin">
                <NavDropdown.Item as={Link} to="/admin/atletas">Atletas</NavDropdown.Item>
                <NavDropdown.Item as={Link} to="/moderacao">Moderação de partidas</NavDropdown.Item>
              </NavDropdown>
            )}
          </Nav>
          <Nav>
            <NavDropdown title={usuario?.nome || "Conta"} id="menu-usuario" align="end">
              <NavDropdown.Item as={Link} to="/perfil">Meu perfil</NavDropdown.Item>
              <NavDropdown.Divider />
              <NavDropdown.Item onClick={sair}>Sair</NavDropdown.Item>
            </NavDropdown>
          </Nav>
        </BsNavbar.Collapse>
      </Container>
    </BsNavbar>
  );
}
