from flask import render_template
from flask import Blueprint
from flask import url_for
from flask import request
from flask import redirect
from .models import Role
from .models import db
from .models import User
import io
from flask import make_response
from xhtml2pdf import pisa

routes_pb = Blueprint("routes", __name__)



@routes_pb.route("/")
def index():
    # 1. Grab all roles from the database
    all_roles = Role.query.all()

    # 2. Pass 'all_roles' into your index.html file
    return render_template("index.html", roles=all_roles)




@routes_pb.route("/admin", methods=["GET", "POST"])
def admin():
    #checking the request
    if request.method == "POST":
        # 1. Grab the data from the admin form
        title = request.form.get('role_title')  # Make sure your HTML input name is 'role_title'
        spots = request.form.get('spots_available')  # Make sure your HTML input name is 'spots_available'
        desc = request.form.get('role_desc')  # Make sure your HTML input name is 'role_desc'

        # 2. Create a new Role object based on your model
        new_role = Role(role=title, description=desc, spots=int(spots))

        # 3. Save it to the database
        db.session.add(new_role)
        db.session.commit()

        print(f"Role '{title}' saved successfully!")
        return redirect(url_for('routes.admin'))

    # --- THIS IS THE NEW GET PART ---
    # 1. Grab all registered users from the database
    all_users = User.query.all()

    # NEW: 2. Grab all created roles from the database too!
    all_roles = Role.query.all()

    #if its GET just show the page
    return render_template("admin.html", users=all_users, roles=all_roles)




#register fro a role
@routes_pb.route("/register", methods=["POST"])
def register():
    user_name = request.form.get('full_name')
    user_email = request.form.get('student_email')
    selected_role = request.form.get('role_name')

    matched_role = Role.query.filter_by(role=selected_role).first()
    if matched_role:

        # NEW: 2. Check if there are actually spots left!
        if matched_role.spots > 0:
            new_user = User(name=user_name, email=user_email,
                            role_id=matched_role.id)  # This links the user to the specific role

            db.session.add(new_user)

            # NEW: 3. Subtract 1 spot from the matched role!
            matched_role.spots = matched_role.spots - 1

            db.session.commit()

    return redirect(url_for('routes.index'))


@routes_pb.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user_to_delete = User.query.get(user_id)

    if user_to_delete:
        """find the role the user was in"""
        matched_role = db.session.get(Role, user_to_delete.role_id)

        if matched_role:
            matched_role.spots = matched_role.spots + 1

        db.session.delete(user_to_delete)
        db.session.commit()

    return redirect(url_for('routes.admin'))


# Add this at the bottom of your Python routes file!
@routes_pb.route("/delete-role/<int:role_id>", methods=["POST"])
def delete_role(role_id):
    # 1. Grab the role from the DB
    role_to_delete = db.session.get(Role, role_id)

    if role_to_delete:
        # 2. Safety check: What if users are already registered for this role?
        # Let's find any users attached to this role and clear their role link
        linked_users = User.query.filter_by(role_id=role_id).all()
        for user in linked_users:
            # You can either delete the users or set their role_id to None.
            # Let's just delete them to keep your DB perfectly clean.
            db.session.delete(user)

        # 3. Delete the actual role
        db.session.delete(role_to_delete)
        db.session.commit()
        print(f"Role and its registered users successfully removed.")
    else:
        print("Role not found.")

    return redirect(url_for('routes.admin'))




@routes_pb.route("/export-pdf")
def export_pdf():
    # 1. Grab all registered users from the database
    users = User.query.all()
    
    # Get current date for the report
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # 2. Create the HTML layout for the PDF with professional design
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2.5cm;
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9px;
                    color: #94a3b8;
                }}
            }}
            
            body {{
                font-family: 'Helvetica', 'Arial', sans-serif;
                color: #1e293b;
                line-height: 1.5;
                margin: 0;
                padding: 0;
            }}
            
            /* Header Section */
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 3px solid #3b82f6;
            }}
            
            .logo {{
                font-size: 28px;
                font-weight: 700;
                color: #0f172a;
                letter-spacing: -0.5px;
                margin-bottom: 8px;
            }}
            
            .logo-accent {{
                color: #3b82f6;
            }}
            
            .report-title {{
                font-size: 20px;
                font-weight: 500;
                color: #334155;
                margin-top: 5px;
            }}
            
            .report-meta {{
                font-size: 11px;
                color: #64748b;
                margin-top: 10px;
            }}
            
            /* Stats Cards */
            .stats-container {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 40px;
                gap: 20px;
            }}
            
            .stat-card {{
                flex: 1;
                background: #f8fafc;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                border: 1px solid #e2e8f0;
            }}
            
            .stat-number {{
                font-size: 32px;
                font-weight: 700;
                color: #3b82f6;
                line-height: 1.2;
            }}
            
            .stat-label {{
                font-size: 11px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 8px;
            }}
            
            /* Table Styles */
            .registrations-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 12px;
            }}
            
            .registrations-table th {{
                background: linear-gradient(135deg, #f1f5f9 0%, #e9eef3 100%);
                color: #1e293b;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 10px;
                letter-spacing: 0.8px;
                padding: 14px 12px;
                border-bottom: 2px solid #cbd5e1;
                text-align: left;
            }}
            
            .registrations-table td {{
                padding: 12px;
                border-bottom: 1px solid #e2e8f0;
                color: #334155;
            }}
            
            .registrations-table tr:hover {{
                background-color: #f8fafc;
            }}
            
            .role-badge {{
                display: inline-block;
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                color: #1e40af;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            
            /* Footer */
            .footer {{
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                text-align: center;
            }}
            
            .signature {{
                font-size: 12px;
                font-weight: 600;
                color: #0f172a;
                margin-top: 10px;
            }}
            
            .signature-line {{
                width: 200px;
                height: 1px;
                background: #cbd5e1;
                margin: 15px auto 8px auto;
            }}
            
            /* Empty State */
            .empty-state {{
                text-align: center;
                padding: 60px 20px;
                color: #94a3b8;
            }}
            
            .empty-icon {{
                font-size: 48px;
                margin-bottom: 16px;
            }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="header">
            <div class="logo">
                Ms<span class="logo-accent">STANSLOUS</span>
            </div>
            <div class="report-title">Registration Report</div>
            <div class="report-meta">Generated on {current_date}</div>
        </div>
    """
    
    # Add stats if there are users
    if users:
        total_users = len(users)
        unique_roles = len(set(user.role.role for user in users))
        
        html_content += f"""
        <!-- Statistics Cards -->
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-number">{total_users}</div>
                <div class="stat-label">Total Registrations</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_roles}</div>
                <div class="stat-label">Roles Filled</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{datetime.now().strftime("%b %d")}</div>
                <div class="stat-label">Report Date</div>
            </div>
        </div>
        """
    
    # Table Section
    if users:
        html_content += """
        <table class="registrations-table">
            <thead>
                <tr>
                    <th style="width: 30%">Full Name</th>
                    <th style="width: 40%">Email Address</th>
                    <th style="width: 30%">Selected Role</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for idx, user in enumerate(users, 1):
            html_content += f"""
                <tr>
                    <td style="font-weight: 500;">{user.name}</td>
                    <td>{user.email}</td>
                    <td><span class="role-badge">{user.role.role}</span></td>
                </tr>
            """
        
        html_content += """
            </tbody>
        </table>
        """
    else:
        html_content += """
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <p>No registrations found</p>
            <p style="font-size: 11px; margin-top: 8px;">Register some roles to see them here</p>
        </div>
        """
    
    # Footer
    html_content += f"""
        <div class="footer">
            <div class="signature-line"></div>
            <div class="signature">
                MsSTANSLOUS • Role Assignment System
            </div>
            <p style="font-size: 9px; color: #94a3b8; margin-top: 12px;">
                This report is auto-generated and contains all current registrations.
            </p>
        </div>
    </body>
    </html>
    """

    # 3. Convert HTML to PDF in memory
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

    if pisa_status.err:
        return "Error generating PDF", 500

    pdf_buffer.seek(0)

    # 4. Return the file to the browser as a download
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=registrations_report.pdf'

    return response