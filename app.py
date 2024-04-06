from flask import Flask,redirect,url_for,render_template,request,flash,abort,session,send_file
from flask_session import Session
from key import secret_key,salt1,salt2
from itsdangerous import URLSafeTimedSerializer
from stoken import token
import os
from flask_mysqldb import MySQL
from mail import sendmail
from io import BytesIO
import pandas as pd
import plotly.express as px
app = Flask(__name__)
app.secret_key = 'NSN@2023'
app.config['SESSION_TYPE']='filesystem'   
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='PHW#84#jeor'
app.config['MYSQL_DB']='expense'
Session(app)
mysql=MySQL(app)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        userid=request.form['userid']
        name=request.form['name']
        phone=request.form['pnumber']
        password=request.form['password']
        salary=request.form['salary']
        saving=request.form['saving']
        email=request.form['email']
        cursor=mysql.connection.cursor()
        cursor.execute('select count(*) from register where name=%s',[userid])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from register where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('username already in use')
            return render_template('register.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('register.html')
        data={'userid':userid,'name':name,'phone':phone,'password':password,'salary':salary,'saving':saving,'email':email}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data,salt1),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/userlogin',methods=['GET','POST'])
def login():
    if request.method=='POST':
        print(request.form)
        userid=request.form['userid']
        password=request.form['password']
        cursor=mysql.connection.cursor()
        cursor.execute('SELECT count(*) from register where userid=%s and password=%s',[userid,password])
        count=cursor.fetchone()[0]
        if count==1:
            session['user']=userid
            return redirect(url_for('userpanel'))
            
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt1,max_age=180)
    except Exception as e:
        abort (404,'Link Expired register again')
    else:
        cursor=mysql.connection.cursor()
        email=data['email']
        cursor.execute('select count(*) from register where email=%s',[email])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('login'))
        else:
            cursor.execute('insert into register(userid,name,phone,password,salary,saving,email) values(%s,%s,%s,%s,%s,%s,%s)',[data['userid'],data['name'],data['phone'],data['password'],data['salary'],data['saving'],data['email']])
            mysql.connection.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))

@app.route('/userpanel')
def userpanel():
     if session.get('user'):
        cursor = mysql.connection.cursor()
        cursor.execute('select salary from register where userid=%s',[session.get('user')])
        sal = cursor.fetchone()[0]
        cursor.execute('select saving from register where userid=%s',[session.get('user')])
        save = cursor.fetchone()[0]
        cursor.execute('select expenditure from register where userid=%s',[session.get('user')])
        cost = cursor.fetchone()[0]
        return render_template('userpanel.html',data=sal,data1=save,data2=cost)
     else:
        return redirect(url_for('login'))
@app.route('/expenses',methods=['GET','POST'])
def expense():
    if session.get('user'):
        if request.method=='POST':
            reason = request.form['expenses_Name']
            cost = request.form['cost']
            cursor=mysql.connection.cursor()
            cursor.execute('select salary from register where userid=%s',[session.get('user')])
            data=cursor.fetchone()[0]
            #print(data)
            cursor.execute('select count(*) from expenses where userid=%s',[session.get('user')])
            count=cursor.fetchone()[0]
            #print(count)
            if count>=1:
                cursor.execute('select expenditure from register where userid=%s',[session.get('user')])
                total=cursor.fetchone()[0]
                #print(total)
                #print(int(total)+int(cost))
                if int(cost)<=data and int(total)<=data and ((int(total)+int(cost))<=data): 
                    cursor.execute('insert into expenses(userid,expenses_Name,cost,salary) values(%s,%s,%s,%s)',([session.get('user'),reason,cost,data]))
                    mysql.connection.commit()
                else:
                    flash('The cost or Expenditure is more than the Salary')
            elif int(cost)<=data:
                    cursor.execute('insert into expenses(userid,expenses_Name,cost,salary) values(%s,%s,%s,%s)',([session.get('user'),reason,cost,data]))
                    mysql.connection.commit()
            else:
                flash('Given cost is more than the Salary')
            cursor.execute('select saving from register where userid=%s',[session.get('user')])
            data1=cursor.fetchone()[0]
            cursor.execute('select sum(cost) from expenses where salary = (select salary from register where userid=%s) ',[session.get('user')])
            totalcost=cursor.fetchone()[0]
            print(totalcost)
            if int(cost)<=data and int(totalcost)<=data:
                cursor.execute('update register set saving=%s where userid=%s ',[data-int(totalcost),session.get('user')])
                mysql.connection.commit()
                cursor.execute('update register set expenditure=%s where userid=%s ',[totalcost,session.get('user')])
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('userpanel'))
        return render_template('addexpenses.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/view')
def expview():
    if session.get('user'):
        cursor=mysql.connection.cursor()
        cursor.execute('select * from expenses where userid=%s',[session.get('user'),])
        data=cursor.fetchall()
        print(data)
        cursor.close()
        return render_template('view.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/salary',methods=['GET','POST'])
def updatesalary():
    if session.get('user'):
        if request.method=='POST':
            salary=int(request.form['salary'])
            cost=0
            salary=(-1)*salary if salary <0 else salary
            cursor=mysql.connection.cursor()
            cursor.execute('update register set salary=%s  where userid=%s',[salary,session.get('user'),])
            cursor.execute('update register set expenditure=%s  where userid=%s',[cost,session.get('user'),])
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('userpanel'))

        return render_template('updatesalary.html')
    else:
        return redirect(url_for('login'))
    

@app.route('/updateexpense/<exp_name>',methods=['GET','POST'])
def updateexpense(exp_name):
    if session.get('user'):
        cursor=mysql.connection.cursor()
        cursor.execute("Select cost from expenses where expenses_Name=%s and userid=%s",[exp_name,session.get('user'),])
        existing_expense = cursor.fetchone()[0]
        if request.method=='POST':
            expense=int(request.form['expense'])
            cursor=mysql.connection.cursor()
            cursor.execute('update expenses set cost=%s  where expenses_Name=%s and userid=%s',[expense,exp_name,session.get('user'),])
            mysql.connection.commit()
            cursor.close()
            flash("Expense Updated Success")
            return redirect(url_for('expview'))

        return render_template('updateexpenses.html',existing_expense=existing_expense)
    else:
        return redirect(url_for('login')) 
    
@app.route('/deleteexpense/<exp_name>',methods=['GET','POST'])
def deleteexpense(exp_name):
    if session.get('user'):
        cursor=mysql.connection.cursor()
        cursor.execute('delete from expenses where expenses_Name=%s and userid=%s',[exp_name,session.get('user'),])
        mysql.connection.commit()
        cursor.close()
        flash("Expense Deleted Success!")
        return redirect(url_for('expview'))
    else:
        return redirect(url_for('login'))   

@app.route('/saving',methods=['GET','POST'])
def save():
    if session.get('user'):
        if request.method=='POST':
            saving =int(request.form['saving'])
            cursor=mysql.connection.cursor()
            cursor.execute('update register set saving=%s  where userid=%s',[saving,session.get('user'),])
            cursor.execute('insert into saving(userid,saving) values(%s,%s)',[session.get('user'),saving])
            mysql.connection.commit()
            cursor.close()
            return render_template('saving.html')
            return redirect(url_for('userpanel'))
    else:
        return redirect(url_for('login'))
    return render_template('saving.html')

# Function to fetch data from MySQL
def fetch_data(query, params=None):
    cursor = mysql.connection.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))

    user_id = session.get('user')

    # Fetching data from MySQL for expenses distribution (Bar Chart)
    expenses_data = fetch_data("SELECT expenses_Name, cost FROM expenses WHERE userid = %s", [user_id])

    # Convert fetched data to DataFrame
    expenses_df = pd.DataFrame(expenses_data, columns=['expenses_Name', 'cost'])

    # Group by expenses and sum the costs for bar chart
    expenses_grouped = expenses_df.groupby('expenses_Name').sum().reset_index()

    # Generating bar chart for expenses distribution
    expenses_bar_chart = px.bar(
        expenses_grouped, 
        x='expenses_Name', 
        y='cost', 
        title='Expenses Distribution (Bar Chart)',
        labels={'expenses_Name': 'Expense Name', 'cost': 'Total Cost'},
        hover_data={'expenses_Name': True, 'cost': ':,.2f'},
        width=800,  # Adjust plot width
        height=400,  # Adjust plot height
        color='expenses_Name'  # Color by expense name
    )

    # Convert Plotly figure to HTML
    expenses_bar_chart_html = expenses_bar_chart.to_html(full_html=False)

    # Fetching data from MySQL for savings
    saving_data = fetch_data("SELECT saving FROM saving WHERE userid = %s", [user_id])

    # Convert fetched data to DataFrame
    saving_df = pd.DataFrame(saving_data, columns=['saving'])

    # Generating pie chart for savings distribution
    saving_pie_chart = px.pie(saving_df, values='saving', names=saving_df['saving'], title='Savings Distribution (Pie Chart)')

    # Convert Plotly figure to HTML
    saving_pie_chart_html = saving_pie_chart.to_html(full_html=False)

    # Fetching data from MySQL for income (assumed to be the salary from the register table)
    salary_data = fetch_data("SELECT salary FROM register WHERE userid = %s", [user_id])

    # Convert fetched data to DataFrame
    salary_df = pd.DataFrame(salary_data, columns=['salary'])

    # Generating pie chart for income distribution
    salary_pie_chart = px.pie(salary_df, values='salary', names=['Income'], title='Income Distribution (Pie Chart)')

    # Convert Plotly figure to HTML
    salary_pie_chart_html = salary_pie_chart.to_html(full_html=False)

    
    return render_template('dashboard.html', 
                           expenses_bar_chart_html=expenses_bar_chart_html,
                           saving_pie_chart_html=saving_pie_chart_html,
                           salary_pie_chart_html = salary_pie_chart_html
                            )


@app.route('/logout')
def logout():
    if session.pop('user'):
        return redirect(url_for('home'))

if __name__=='__main__':
    app.run(use_reloader=True,debug=True)
