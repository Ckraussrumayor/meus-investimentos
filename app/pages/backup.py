"""
Página de Backup & Restauração – Exportar e importar dados do aplicativo.
"""

import json
from datetime import datetime

import streamlit as st

from app.services.backup_service import export_all_data, import_all_data


def render():
    """Renderiza a página de Backup & Restauração."""
    st.markdown("## 💾 Backup & Restauração")
    st.markdown(
        "Exporte seus dados para um arquivo JSON e reimporte-os quando necessário "
        "(ex.: após hibernação do deploy gratuito)."
    )
    st.markdown("---")

    tab_export, tab_import = st.tabs(["📤 Exportar", "📥 Importar"])

    with tab_export:
        _render_export()

    with tab_import:
        _render_import()


def _render_export():
    """Seção de exportação de dados."""
    st.markdown("### 📤 Exportar Dados")
    st.info(
        "O arquivo exportado contém todos os seus cadastros, cenários, "
        "simulações, histórico e configurações. "
        "Guarde-o em local seguro para restaurar quando precisar."
    )

    if st.button("🔄 Gerar Backup", use_container_width=True, type="primary"):
        try:
            data = export_all_data()
            st.session_state["_backup_data"] = data
            st.session_state["_backup_ready"] = True
        except Exception as e:
            st.error(f"Erro ao gerar backup: {e}")
            return

    if st.session_state.get("_backup_ready"):
        data = st.session_state["_backup_data"]

        # Resumo
        n_assets = len(data.get("asset_classes", []))
        n_scenarios = len(data.get("scenarios", []))
        n_snapshots = len(data.get("historical_snapshots", []))
        n_proj = sum(
            len(s.get("projections", [])) for s in data.get("scenarios", [])
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ativos", n_assets)
        col2.metric("Cenários", n_scenarios)
        col3.metric("Projeções", n_proj)
        col4.metric("Snapshots", n_snapshots)

        # Botão de download
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        filename = f"backup_investimentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        st.download_button(
            label="⬇️ Baixar Arquivo de Backup",
            data=json_str,
            file_name=filename,
            mime="application/json",
            use_container_width=True,
        )


def _render_import():
    """Seção de importação de dados."""
    st.markdown("### 📥 Importar Dados")
    st.warning(
        "⚠️ A importação **substitui todos os dados atuais** "
        "(cadastros, cenários, simulações e histórico). "
        "Faça um backup antes de prosseguir, se necessário."
    )

    uploaded = st.file_uploader(
        "Selecione o arquivo de backup (.json)",
        type=["json"],
        key="backup_upload",
    )

    if uploaded is not None:
        try:
            content = uploaded.read().decode("utf-8")
            data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            st.error("Arquivo inválido. Certifique-se de que é um JSON válido.")
            return

        # Validação básica
        if "export_version" not in data:
            st.error("Este arquivo não parece ser um backup válido do Simulador.")
            return

        # Pré-visualização
        st.markdown("**Conteúdo do backup:**")
        n_assets = len(data.get("asset_classes", []))
        n_scenarios = len(data.get("scenarios", []))
        n_snapshots = len(data.get("historical_snapshots", []))
        n_proj = sum(
            len(s.get("projections", [])) for s in data.get("scenarios", [])
        )
        export_date = data.get("export_date", "N/A")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ativos", n_assets)
        col2.metric("Cenários", n_scenarios)
        col3.metric("Projeções", n_proj)
        col4.metric("Snapshots", n_snapshots)
        st.caption(f"Backup gerado em: {export_date}")

        st.markdown("---")

        # Confirmação
        confirm = st.checkbox(
            "Confirmo que desejo substituir todos os dados atuais pelo backup acima."
        )

        if st.button(
            "🔄 Restaurar Backup",
            use_container_width=True,
            type="primary",
            disabled=not confirm,
        ):
            try:
                counts = import_all_data(data)
                st.success(
                    f"✅ Backup restaurado com sucesso! "
                    f"Importados: {counts.get('asset_classes', 0)} ativos, "
                    f"{counts.get('scenarios', 0)} cenários, "
                    f"{counts.get('projections', 0)} projeções, "
                    f"{counts.get('historical_snapshots', 0)} snapshots."
                )
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao restaurar backup: {e}")
