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
    # Handle POST request (create new role)
    if request.method == "POST":
        title = request.form.get('role_title')
        spots = request.form.get('spots_available')
        desc = request.form.get('role_desc')
        
        new_role = Role(role=title, description=desc, spots=int(spots))
        db.session.add(new_role)
        db.session.commit()
        
        print(f"Role '{title}' saved successfully!")
        return redirect(url_for('routes.admin'))
    
    # Handle GET request - with pagination
    # Get page number from URL, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 users per page
    
    # Get paginated users
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    total_users = pagination.total
    total_pages = pagination.pages
    
    # Get all roles (no pagination needed for roles)
    all_roles = Role.query.all()
    
    return render_template(
        "admin.html", 
        users=users, 
        roles=all_roles,
        pagination=pagination,
        current_page=page,
        total_pages=total_pages,
        total_users=total_users,
        per_page=per_page
    )



@routes_pb.route("/admin/data")
def admin_data():
    """AJAX endpoint for smooth pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    # Render just the table HTML (no full page)
    html = render_template("admin_table.html", users=users)
    
    return {
        "html": html,
        "current_page": page,
        "total_pages": pagination.pages,
        "total_users": pagination.total,
        "per_page": per_page
    }




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
    
    # Count total registrations and unique roles
    total_users = len(users)
    unique_roles = len(set(user.role.role for user in users)) if users else 0

    # 2. Create the HTML layout for the PDF with professional table design
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Registrations Report</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
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
            
            /* Header */
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 3px solid #2563eb;
            }}
            
            .title {{
                font-size: 28px;
                font-weight: bold;
                color: #0f172a;
                margin-bottom: 5px;
            }}
            
            .subtitle {{
                font-size: 14px;
                color: #64748b;
                margin-top: 5px;
            }}
            
            .date {{
                font-size: 11px;
                color: #94a3b8;
                margin-top: 8px;
            }}
            
            /* Stats Cards */
            .stats-container {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 35px;
                gap: 15px;
            }}
            
            .stat-card {{
                flex: 1;
                background: #f8fafc;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
                border: 1px solid #e2e8f0;
            }}
            
            .stat-number {{
                font-size: 32px;
                font-weight: bold;
                color: #2563eb;
                line-height: 1.2;
            }}
            
            .stat-label {{
                font-size: 10px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 5px;
            }}
            
            /* Table Styles - Professional Design */
            .registrations-table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                margin: 25px 0;
                font-size: 12px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }}
            
            .registrations-table th {{
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                color: white;
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 0.5px;
                padding: 14px 16px;
                text-align: left;
            }}
            
            .registrations-table td {{
                padding: 12px 16px;
                background-color: white;
                border-bottom: 1px solid #e2e8f0;
                color: #334155;
            }}
            
            .registrations-table tr:last-child td {{
                border-bottom: none;
            }}
            
            .registrations-table tr:hover td {{
                background-color: #f8fafc;
            }}
            
            /* Zebra striping for better readability */
            .registrations-table tr:nth-child(even) td {{
                background-color: #fafafa;
            }}
            
            .registrations-table tr:nth-child(even):hover td {{
                background-color: #f5f5f5;
            }}
            
            .role-badge {{
                display: inline-block;
                background: #dbeafe;
                color: #1e40af;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
            
            /* Footer with Signatures */
            .footer {{
                margin-top: 50px;
                padding-top: 30px;
            }}
            
            .signatures-container {{
                display: flex;
                justify-content: space-between;
                gap: 40px;
                margin-top: 20px;
            }}
            
            .signature-box {{
                flex: 1;
                text-align: center;
            }}
            
            .signature-line {{
                width: 80%;
                margin: 0 auto 8px auto;
                border-top: 1px solid #cbd5e1;
            }}
            
            .signature-name {{
                font-size: 12px;
                font-weight: 600;
                color: #0f172a;
                margin-bottom: 4px;
            }}
            
            .signature-title {{
                font-size: 9px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .signature-date {{
                font-size: 8px;
                color: #94a3b8;
                margin-top: 5px;
            }}
            
            .stamp {{
                font-size: 10px;
                color: #2563eb;
                font-weight: bold;
                margin-top: 8px;
                letter-spacing: 1px;
            }}
            
            /* Empty state */
            .empty-state {{
                text-align: center;
                padding: 50px 20px;
                color: #94a3b8;
            }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="header">
            <div class="title">Registrations Report</div>
            <div class="subtitle">Role Assignment System</div>
            <div class="date">Generated on {current_date}</div>
        </div>
    """
    
    # Add statistics cards if there are users
    if users:
        html_content += f"""
        <!-- Statistics -->
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
                <div class="stat-number">{datetime.now().strftime("%b %d, %Y")}</div>
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
                    <th style="width: 45%">Email Address</th>
                    <th style="width: 25%">Selected Role</th>
                 </tr>
            </thead>
            <tbody>
        """
        
        for user in users:
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
            <p>No registrations found in the system.</p>
            <p style="font-size: 11px; margin-top: 8px;">Register some roles to see them here</p>
        </div>
        """
    
    # Footer with TWO Signatures - MsSTANSLOUS on left, Rejoice on right
    html_content += f"""
        <div class="footer">
            <div class="signatures-container">
                <!-- Left Signature - MsSTANSLOUS -->
                <div class="signature-box">
                    <div class="signature-line"></div>
                    <div class="signature-name">MsSTANSLOUS</div>
                    <div class="signature-title">System Developer</div>
                    <div class="signature-date">Generated: {current_date}</div>
                    <div class="stamp">✦ DIGITAL SIGNATURE ✦</div>
                </div>
                
                <!-- Right Signature - System Admin Rejoice -->
                <div class="signature-box">
                    <div class="signature-line"></div>
                    <div class="signature-name">Rejoice</div>
                    <div class="signature-title">System Administrator</div>
                    <div class="signature-date">Authorized: {datetime.now().strftime("%B %d, %Y")}</div>
                    <div class="stamp">✓ APPROVED ✓</div>
                </div>
            </div>
            
            <!-- Report Footer Note -->
            <div style="text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                <p style="font-size: 8px; color: #94a3b8; margin: 0;">
                    This is a computer-generated document. No physical signature is required.
                </p>
                <p style="font-size: 8px; color: #94a3b8; margin: 5px 0 0 0;">
                    Role Assignment System • MsSTANSLOUS • All Rights Reserved
                </p>
            </div>
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