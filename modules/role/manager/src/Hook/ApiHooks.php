<?php

declare(strict_types=1);

namespace Drupal\farm_manager\Hook;

use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * API hook implementations for farm_manager.
 */
class ApiHooks {

  public function __construct(
    protected ModuleHandlerInterface $moduleHandler,
  ) {}

  /**
   * Implements hook_oauth2_scope_info_alter().
   */
  #[Hook('oauth2_scope_info_alter')]
  public function oauth2ScopeInfoAlter(array &$scopes) {

    // Enable the password grant for static role scopes.
    if ($this->moduleHandler->moduleExists('simple_oauth_password_grant')) {
      $target_scopes = [
        'farm_manager',
      ];
      foreach ($target_scopes as $scope_id) {
        if (isset($scopes[$scope_id])) {
          $scopes[$scope_id]['grant_types']['password'] = [
            'status' => TRUE,
          ];
        }
      }
    }
  }

}
