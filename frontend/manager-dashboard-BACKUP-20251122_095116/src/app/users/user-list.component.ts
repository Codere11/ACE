import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UsersService } from '../services/users.service';
import { User } from '../models/user.model';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="user-list">
      <h1>Team Members</h1>
      
      @if (loading) {
        <p>Loading users...</p>
      } @else {
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (user of users; track user.id) {
              <tr>
                <td>{{user.username}}</td>
                <td>{{user.email}}</td>
                <td>
                  <span class="badge" [class.admin]="user.role === 'org_admin'">
                    {{user.role}}
                  </span>
                </td>
                <td>
                  <span [class.active]="user.is_active" [class.inactive]="!user.is_active">
                    {{user.is_active ? 'Active' : 'Inactive'}}
                  </span>
                </td>
                <td>
                  <button>Edit</button>
                  <button>Delete</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>
  `,
  styles: [`
    .user-list {
      background: white;
      padding: 30px;
      border-radius: 8px;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    
    .badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      background: #3498db;
      color: white;
    }
    
    .badge.admin {
      background: #e74c3c;
    }
    
    .active {
      color: green;
    }
    
    .inactive {
      color: red;
    }
  `]
})
export class UserListComponent implements OnInit {
  users: User[] = [];
  loading = true;

  constructor(private usersService: UsersService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.usersService.listUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading users:', err);
        this.loading = false;
      }
    });
  }
}
