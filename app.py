import sqlite3  # Importa a biblioteca sqlite3 para trabalhar com o banco de dados SQLite
from flask import Flask, render_template, request, redirect, url_for, flash  # Importa as funcionalidades do Flask para criar o aplicativo web
from datetime import datetime  # Importa a classe datetime para trabalhar com datas e horas

app = Flask(__name__)  # Cria uma instância da aplicação Flask
app.secret_key = 'supersecretkey'  # Chave secreta necessária para usar flash messages

DATABASE = 'historico.db'  # Nome do arquivo do banco de dados SQLite

# Função para conectar ao banco de dados SQLite
# def connect_db():
#     return sqlite3.connect(DATABASE)
def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acessar os resultados por nome de coluna
    return conn


# Função para criar a tabela, se não existir
def create_table():
    with connect_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidade TEXT NOT NULL,
                poco TEXT NOT NULL,
                resultado REAL NOT NULL,
                resultado_bbl REAL NOT NULL,
                data_hora TEXT NOT NULL
            )
        ''')
        conn.commit()

create_table()  # Cria a tabela ao iniciar o aplicativo

# Função para calcular o volume baseado na distância e na opção selecionada
def calcular_volume(distancia, opcao):
    # Dicionário que mapeia cada opção a um fator de multiplicação
    fatores = {"1": 2.019, "2": 3.020, "3": 4.513}
    if opcao not in fatores:  # Verifica se a opção selecionada é válida
        raise ValueError("Opção inválida")  # Lança um erro se a opção for inválida
    return distancia * fatores[opcao]  # Retorna o resultado do cálculo

# Rota principal para a página inicial
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None  # Variável para armazenar o resultado do cálculo
    resultado_bbl = None  # Variável para armazenar o resultado convertido para BBL
    cidade = ""  # Variável para armazenar o nome da cidade
    poco = ""  # Variável para armazenar o nome do poço

     
    if request.method == "POST":  # Se o método da requisição for POST, processa os dados do formulário
        try:
            # Coleta e converte os dados enviados pelo formulário
            distancia = float(request.form["input"])
            opcao = request.form["opcoes"]
            cidade = request.form["nome_cidade"]
            poco = request.form["nome_poco"]

            resultado = calcular_volume(distancia, opcao)  # Calcula o volume
            resultado_formatado = round(resultado, 1)  # Formata o resultado com uma casa decimal
            resultado_bbl = round(resultado / 158.987, 1)  # Converte o resultado de Litros para BBL

            # Insere o resultado no banco de dados
            with connect_db() as conn:
                conn.execute('''
                    INSERT INTO resultados (cidade, poco, resultado, resultado_bbl, data_hora)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cidade, poco, resultado_formatado, resultado_bbl, datetime.now().strftime('%d/%m/%Y %H:%M:%S')))
                conn.commit()

                # Limita o histórico aos últimos 10 resultados
                conn.execute('''
                    DELETE FROM resultados 
                    WHERE id NOT IN (
                        SELECT id FROM resultados 
                        ORDER BY id DESC 
                        LIMIT 15
                    )
                ''')
                conn.commit()

            flash("Resultado salvo com sucesso!", "success")  # Mostra uma mensagem de sucesso
        except ValueError as ve:  # Captura erros de valor inválido
            flash(f"Erro: {ve}", "error")  # Mostra uma mensagem de erro
        except Exception as e:  # Captura qualquer outro erro
            flash(f"Ocorreu um erro: {e}", "error")  # Mostra uma mensagem de erro

    # Renderiza a página inicial com os resultados
    return render_template("index.html", resultado=resultado, resultado_bbl=resultado_bbl, cidade=cidade, poco=poco)

# Rota para exibir o histórico de resultados
@app.route("/historico")
def historico():
    with connect_db() as conn:  # Conecta ao banco de dados
        cursor = conn.execute('SELECT * FROM resultados ORDER BY id DESC')  # Consulta os resultados ordenados por ID em ordem decrescente
        historico_resultados = cursor.fetchall()  # Recupera todos os resultados
    return render_template("historico.html", historico=historico_resultados)  # Renderiza a página de histórico com os resultados

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


# Rota para deletar um resultado específico
@app.route("/delete_result/<int:id>", methods=["POST"])
def delete_result(id):
    with connect_db() as conn:  # Conecta ao banco de dados
        conn.execute('DELETE FROM resultados WHERE id = ?', (id,))  # Deleta o resultado com o ID fornecido
        conn.commit()
    flash("Resultado deletado com sucesso!", "success")  # Mostra uma mensagem de sucesso
    return redirect(url_for('historico'))  # Redireciona para a página de histórico

# Rota para editar um resultado específico
@app.route("/edit_result/<int:id>", methods=["GET", "POST"])
def edit_result(id):
    if request.method == "POST":  # Se o método da requisição for POST, processa os dados enviados pelo formulário
        cidade = request.form["cidade"]  # Coleta o nome da cidade
        poco = request.form["poco"]  # Coleta o nome do poço
        try:
            # Tenta converter os resultados para números float
            resultado = float(request.form["resultado"])
            resultado_bbl = float(request.form["resultado_bbl"])
        except ValueError:
            flash("Erro: Os resultados devem ser numéricos.", "error")  # Mostra uma mensagem de erro se a conversão falhar
            return redirect(url_for('edit_result', id=id))
        
        with connect_db() as conn:  # Conecta ao banco de dados
            # Atualiza o resultado com os novos dados fornecidos
            conn.execute('''
                UPDATE resultados 
                SET cidade = ?, poco = ?, resultado = ?, resultado_bbl = ?, data_hora = ?
                WHERE id = ?
            ''', (cidade, poco, resultado, resultado_bbl, datetime.now().strftime('%d/%m/%Y %H:%M:%S'), id))
            conn.commit()
        flash("Resultado atualizado com sucesso!", "success")  # Mostra uma mensagem de sucesso
        return redirect(url_for('historico'))  # Redireciona para a página de histórico

    with connect_db() as conn:  # Conecta ao banco de dados
        cursor = conn.execute('SELECT * FROM resultados WHERE id = ?', (id,))  # Recupera o resultado com o ID fornecido
        result = cursor.fetchone()  # Armazena o resultado encontrado
    if result:
        return render_template("edit.html", resultado=result)  # Renderiza a página de edição com os dados do resultado
    else:
        flash("Resultado não encontrado.", "error")  # Mostra uma mensagem de erro se o resultado não for encontrado
        return redirect(url_for('historico'))  # Redireciona para a página de histórico

if __name__ == "__main__":
    app.run(debug=True)  # Inicia o servidor Flask em modo de depuração
