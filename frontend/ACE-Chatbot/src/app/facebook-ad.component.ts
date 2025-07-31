import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-facebook-ad',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './facebook-ad.component.html',
  styleUrls: ['./facebook-ad.component.scss']
})
export class FacebookAdComponent {
  constructor(private router: Router) {}

  handleClick() {
    this.router.navigate(['/chat']);
  }
}
