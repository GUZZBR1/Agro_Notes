<?php

declare(strict_types=1);

namespace Drupal\farm_l10n\Form;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Config\TypedConfigManagerInterface;
use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\language\Form\NegotiationSelectedForm;

/**
 * Configure the selected language negotiation method for this site.
 *
 * @see \Drupal\language\Form\NegotiationSelectedForm
 *
 * PHPStan throws the following error on the next line:
 * Class Drupal\farm_l10n\Form\L10nSettingsForm extends @internal class
 * Drupal\language\Form\NegotiationSelectedForm.
 * We ignore this because we intentionally extend the core
 * NegotiationSelectedForm, even though it is marked @internal, and take
 * responsibility for it working correctly.
 * @phpstan-ignore-next-line
 */
class L10nSettingsForm extends NegotiationSelectedForm {

  use AutowireTrait;

  public function __construct(
    ConfigFactoryInterface $config_factory,
    protected TypedConfigManagerInterface $typedConfigManager,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {
    parent::__construct($config_factory, $typedConfigManager);
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_l10n_settings_form';
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state) {
    $form = parent::buildForm($form, $form_state);

    // Provide an option to update the default language of existing users.
    $form['update_existing_users'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Update existing users'),
      '#description' => $this->t('Update the language of all existing users to match the default language.'),
      '#default_value' => FALSE,
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {
    parent::submitForm($form, $form_state);

    // Initiate a batch operation to update the default language of all users
    // (except user 1).
    if ($form_state->getValue('update_existing_users')) {
      $operations = [];
      $query = $this->entityTypeManager->getStorage('user')->getQuery()->accessCheck(FALSE);
      $uids = $query->condition('uid', '1', '!=')->execute();
      foreach ($uids as $uid) {
        $operations[] = [
          [__CLASS__, 'updateUserLanguage'],
          [$uid, $form_state->getValue('selected_langcode')],
        ];
      }
      batch_set([
        'operations' => $operations,
        'title' => $this->t('Updating user languages'),
        'error_message' => $this->t('The user language update has encountered an error.'),
      ]);
    }
  }

  /**
   * Update the language for a user.
   *
   * @param int $uid
   *   The user ID.
   * @param string $langcode
   *   The new langcode to assign.
   */
  public static function updateUserLanguage(int $uid, string $langcode) {
    /** @var \Drupal\user\UserInterface $user */
    $user = \Drupal::entityTypeManager()->getStorage('user')->load($uid);
    $user->set('preferred_langcode', $langcode);
    $user->set('preferred_admin_langcode', $langcode);
    $user->save();
  }

}
