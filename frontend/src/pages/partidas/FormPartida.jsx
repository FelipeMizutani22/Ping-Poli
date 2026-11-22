import { useEffect, useState } from "react";
import { Alert, Button, ButtonGroup, Card, Col, Form, Row, ToggleButton } from "react-bootstrap";
import { useNavigate } from "react-router-dom";

import { listarCampeonatos } from "../../api/competicoes";
import { registrarPartida } from "../../api/partidas";
import BuscaAtleta from "../../components/BuscaAtleta";
import ErroCampo from "../../components/ErroCampo";
import { hojeISO } from "../../utils/formatacao";
import { linhasVazias, setsDasLinhas } from "../../utils/partidas";
import BuscaExterno from "./BuscaExterno";
import EntradaPlacar from "./EntradaPlacar";
import ErrosPlacar from "./ErrosPlacar";

const FORM_INICIAL = {
  data_jogo: hojeISO(),
  campeonato: "",
  categoria: "",
  fase: "",
  tipo_adversario: "poli",
  formato: "5",
  observacoes: "",
};

// UC15 · Registrar partida
export default function FormPartida() {
  const navigate = useNavigate();
  const [form, setForm] = useState(FORM_INICIAL);
  const [adversario, setAdversario] = useState(null);
  const [externo, setExterno] = useState(null);
  const [linhas, setLinhas] = useState(linhasVazias(5));
  const [campeonatos, setCampeonatos] = useState([]);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  // Campeonatos cadastrados (Trilha D). Enquanto a API não existir, fica só "Amistoso/Treino".
  useEffect(() => {
    listarCampeonatos().then((lista) => setCampeonatos(Array.isArray(lista) ? lista : lista?.results || [])).catch(() => {});
  }, []);

  const campeonatoEscolhido = campeonatos.find((c) => String(c.id) === form.campeonato);
  const categorias = campeonatoEscolhido?.categorias || [];

  function alterar(e) {
    const { name, value } = e.target;
    const novo = { ...form, [name]: value };
    if (name === "campeonato") novo.categoria = "";
    if (name === "formato") setLinhas(linhasVazias(value));
    setForm(novo);
  }

  async function salvar(e) {
    e.preventDefault();
    setErro(null);
    const { sets, erro: erroLinhas } = setsDasLinhas(linhas);
    if (erroLinhas) {
      setErro({ message: "Corrija o placar.", campos: { sets: [erroLinhas] } });
      return;
    }
    const poli = form.tipo_adversario === "poli";
    const dados = {
      data_jogo: form.data_jogo,
      campeonato: form.campeonato ? Number(form.campeonato) : null,
      categoria: form.categoria ? Number(form.categoria) : null,
      fase: form.fase.trim(),
      tipo_adversario: form.tipo_adversario,
      adversario: poli ? adversario?.id ?? null : null,
      adversario_externo: poli ? null : externo?.id ?? null,
      formato: Number(form.formato),
      sets,
      observacoes: form.observacoes.trim(),
    };
    setEnviando(true);
    try {
      const partida = await registrarPartida(dados);
      const mensagem = partida.status === "pendente"
        ? "Partida registrada. Aguardando confirmação do adversário"
        : "Partida registrada";
      navigate(`/partidas/${partida.id}`, { state: { mensagem } });
    } catch (falha) {
      setErro(falha);
    } finally {
      setEnviando(false);
    }
  }

  const campos = erro?.campos || {};
  const poli = form.tipo_adversario === "poli";

  return (
    <Card>
      <Card.Body>
        <h1 className="h4 mb-4">Registrar partida</h1>
        {erro && <Alert variant="danger">{erro.status === 400 ? "Confira os campos destacados." : erro.message}</Alert>}

        <Form noValidate onSubmit={salvar}>
          <Row className="g-3">
            <Col md={4}>
              <Form.Group controlId="data_jogo">
                <Form.Label>Data *</Form.Label>
                <Form.Control type="date" name="data_jogo" max={hojeISO()} value={form.data_jogo}
                  onChange={alterar} isInvalid={Boolean(campos.data_jogo)} />
                <ErroCampo erro={erro} campo="data_jogo" />
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group controlId="campeonato">
                <Form.Label>Competição *</Form.Label>
                <Form.Select name="campeonato" value={form.campeonato} onChange={alterar}>
                  <option value="">Amistoso/Treino</option>
                  {campeonatos.map((c) => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            {form.campeonato && (
              <Col md={4}>
                <Form.Group controlId="categoria">
                  <Form.Label>Categoria</Form.Label>
                  <Form.Select name="categoria" value={form.categoria} onChange={alterar}
                    isInvalid={Boolean(campos.categoria)}>
                    <option value="">—</option>
                    {categorias.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome}</option>
                    ))}
                  </Form.Select>
                  <ErroCampo erro={erro} campo="categoria" />
                </Form.Group>
              </Col>
            )}
            <Col md={4}>
              <Form.Group controlId="fase">
                <Form.Label>Fase</Form.Label>
                <Form.Control name="fase" maxLength={50} placeholder="Ex.: Oitavas de final"
                  value={form.fase} onChange={alterar} />
              </Form.Group>
            </Col>

            <Col md={8}>
              <Form.Label className="d-block">Tipo de adversário *</Form.Label>
              <ButtonGroup>
                {[["poli", "Poli-USP"], ["externo", "Externo"]].map(([valor, texto]) => (
                  <ToggleButton key={valor} id={`tipo-${valor}`} type="radio" variant="outline-primary"
                    name="tipo_adversario" value={valor} checked={form.tipo_adversario === valor} onChange={alterar}>
                    {texto}
                  </ToggleButton>
                ))}
              </ButtonGroup>
            </Col>

            <Col md={8}>
              <Form.Label>Adversário *</Form.Label>
              {poli ? (
                <BuscaAtleta valor={adversario} onSelect={setAdversario} isInvalid={Boolean(campos.adversario)} />
              ) : (
                <BuscaExterno valor={externo} onSelect={setExterno} isInvalid={Boolean(campos.adversario_externo)} />
              )}
              <ErroCampo erro={erro} campo={poli ? "adversario" : "adversario_externo"} />
            </Col>
            <Col md={4}>
              <Form.Group controlId="formato">
                <Form.Label>Formato *</Form.Label>
                <Form.Select name="formato" value={form.formato} onChange={alterar}>
                  <option value="3">Melhor de 3</option>
                  <option value="5">Melhor de 5</option>
                  <option value="7">Melhor de 7</option>
                </Form.Select>
              </Form.Group>
            </Col>

            <Col xs={12}>
              <Form.Label>Placar *</Form.Label>
              <EntradaPlacar linhas={linhas} onChange={setLinhas}
                rotuloAdversario={(poli ? adversario?.nome : externo?.nome) || "Adversário"} />
              <ErrosPlacar mensagens={campos.sets} />
            </Col>

            <Col xs={12}>
              <Form.Group controlId="observacoes">
                <Form.Label>Observações</Form.Label>
                <Form.Control as="textarea" rows={2} name="observacoes" maxLength={300}
                  value={form.observacoes} onChange={alterar} />
              </Form.Group>
            </Col>
          </Row>

          <div className="d-flex gap-2 mt-4">
            <Button type="submit" disabled={enviando}>{enviando ? "Salvando..." : "Salvar"}</Button>
            <Button variant="outline-secondary" onClick={() => navigate(-1)}>Cancelar</Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}
