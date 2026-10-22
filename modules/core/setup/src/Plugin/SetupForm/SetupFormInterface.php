<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\SetupForm;

use Drupal\Core\Form\FormInterface;
use Drupal\Core\Session\AccountInterface;

/**
 * Interface for setup forms.
 */
interface SetupFormInterface extends FormInterface {

  /**
   * Returns the setup form title.
   *
   * @return string
   *   The setup form title.
   */
  public function getTitle();

  /**
   * Returns the setup form task title.
   *
   * @return string
   *   The setup form task title.
   */
  public function getTaskTitle();

  /**
   * Returns the setup form description.
   *
   * @return string
   *   The setup form description.
   */
  public function getDescription();

  /**
   * Checks access for the setup form.
   *
   * @param \Drupal\Core\Session\AccountInterface $account
   *   Run access checks for this account.
   *
   * @return \Drupal\Core\Access\AccessResultInterface
   *   The access result.
   */
  public function access(AccountInterface $account);

}
